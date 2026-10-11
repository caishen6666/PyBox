# -*- coding: utf-8 -*-
"""PyPI 包管理器：在运行时把纯 Python 包下载并安装到应用私有目录。

原理：从 PyPI JSON API 获取发行版信息，优先选择纯 Python wheel
（*.py3-none-any / *.py2.py3-none-any，本质是 zip），解压到 site-packages
并加入 sys.path；其次尝试 sdist（tar.gz）中直接可用的包目录。
"""
import io
import json
import os
import re
import sys
import tarfile
import threading
import urllib.request
import zipfile

PYPI_JSON = "https://pypi.org/pypi/{name}/json"
USER_AGENT = "Mozilla/5.0 (PyBox/1.0)"

# 顶层目录/文件黑名单：解压 wheel 时不拷贝这些发行版元数据
_DIST_INFO = re.compile(r"^[^/]+\.(dist-info|egg-info)(/|$)")


def _http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


class PyPIManager:
    """线程化的包安装器。回调与 Downloader 相同风格。"""

    def __init__(self, site_dir, on_log=None, on_done=None, on_error=None):
        self.site_dir = os.path.abspath(site_dir)
        os.makedirs(self.site_dir, exist_ok=True)
        self.meta_file = os.path.join(self.site_dir, "_pybox_packages.json")
        self.on_log = on_log
        self.on_done = on_done
        self.on_error = on_error
        if self.site_dir not in sys.path:
            sys.path.insert(0, self.site_dir)
        self._thread = None

    # ---------- 元数据 ----------
    def _load_meta(self):
        try:
            with open(self.meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_meta(self, meta):
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def installed_packages(self):
        return self._load_meta()

    # ---------- 查询 PyPI ----------
    @staticmethod
    def query(name):
        """返回 (版本, 简介, 文件列表)。失败抛异常。"""
        data = json.loads(_http_get(PYPI_JSON.format(name=name.strip())).decode("utf-8"))
        info = data["info"]
        version = info["version"]
        summary = info.get("summary") or ""
        files = data["releases"].get(version) or []
        return version, summary, files

    @staticmethod
    def pick_file(files):
        """从发行版文件里挑选最适合的文件。

        优先级：纯 Python wheel > 其他 wheel（当前平台不保证可用）> sdist。
        返回 (url, kind)，kind 为 wheel / sdist；找不到返回 None。
        """
        pure_wheels, other_wheels, sdists = [], [], []
        for f in files:
            fn = f.get("filename", "")
            url = f.get("url", "")
            if not url:
                continue
            if fn.endswith(".whl"):
                # xx-version-py3-none-any.whl → 纯 Python
                if re.search(r"-py[23].*-none-any\.whl$", fn) or fn.endswith("py2.py3-none-any.whl"):
                    pure_wheels.append(url)
                else:
                    other_wheels.append(url)
            elif fn.endswith(".tar.gz"):
                sdists.append(url)
        if pure_wheels:
            return pure_wheels[0], "wheel"
        if other_wheels:
            return other_wheels[0], "wheel"
        if sdists:
            return sdists[0], "sdist"
        return None

    # ---------- 安装 / 卸载 ----------
    def install(self, name):
        """后台线程安装包。"""
        if self._thread and self._thread.is_alive():
            if self.on_error:
                self.on_error("已有安装任务在进行")
            return
        self._thread = threading.Thread(
            target=self._install_run, args=(name.strip(),), daemon=True)
        self._thread.start()

    def _log(self, msg):
        if self.on_log:
            try:
                self.on_log(msg)
            except Exception:
                pass

    def _install_run(self, name):
        try:
            self._log("正在查询 PyPI: %s ..." % name)
            version, summary, files = self.query(name)
            picked = self.pick_file(files)
            if not picked:
                raise RuntimeError("该版本没有可自动安装的文件（仅二进制发行版）")
            url, kind = picked
            self._log("找到 %s==%s，下载 %s" % (name, version, url.rsplit("/", 1)[-1]))
            data = _http_get(url)
            installed_tops = []
            if kind == "wheel":
                installed_tops = self._extract_wheel(data)
            else:
                installed_tops = self._extract_sdist(data)
            if not installed_tops:
                raise RuntimeError("压缩包内没有找到可导入的 Python 模块")
            meta = self._load_meta()
            meta[name] = {"version": version, "summary": summary,
                          "tops": installed_tops, "kind": kind}
            self._save_meta(meta)
            self._log("安装完成: %s==%s → %s" % (name, version, ", ".join(installed_tops)))
            # 尝试导入验证
            try:
                __import__(name if name.replace("-", "_") in installed_tops
                           else installed_tops[0])
                self._log("导入验证成功 ✓")
            except Exception as e:
                self._log("注意: 导入验证未通过(%s)，部分依赖可能仍需手动安装" % e)
            if self.on_done:
                self.on_done(name, version)
        except Exception as e:
            self._log("安装失败: %s" % e)
            if self.on_error:
                self.on_error(str(e))

    def _extract_wheel(self, data):
        tops = []
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if info.is_dir() or _DIST_INFO.match(info.filename):
                    continue
                zf.extract(info, self.site_dir)
                top = info.filename.split("/", 1)[0]
                if top not in tops:
                    tops.append(top)
        return tops

    def _extract_sdist(self, data):
        """sdist: tar.gz，根目录形如 name-version/，只拷贝其中的包/模块。"""
        tops = []
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            members = [m for m in tf.getmembers()
                       if m.isfile() or m.isdir()]
            for m in members:
                parts = m.name.split("/")
                if len(parts) < 2:
                    continue
                rel = "/".join(parts[1:])   # 去掉 name-version/ 根目录
                if not rel or rel.startswith((".", "/")):
                    continue
                top = parts[1]
                if top.endswith((".egg-info", ".dist-info")) or top == "setup.py":
                    continue
                target = os.path.join(self.site_dir, rel)
                if m.isdir():
                    os.makedirs(target, exist_ok=True)
                    if top not in tops:
                        tops.append(top)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    fsrc = tf.extractfile(m)
                    with open(target, "wb") as fdst:
                        fdst.write(fsrc.read())
                    if top not in tops:
                        tops.append(top)
        return tops

    def uninstall(self, name):
        meta = self._load_meta()
        entry = meta.pop(name, None)
        if entry is None:
            if self.on_error:
                self.on_error("未安装: %s" % name)
            return False
        for top in entry.get("tops", []):
            path = os.path.join(self.site_dir, top)
            try:
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)
            except OSError as e:
                self._log("删除 %s 失败: %s" % (top, e))
        self._save_meta(meta)
        # 清理模块缓存
        for mod in list(sys.modules):
            if mod.split(".")[0] in entry.get("tops", []):
                del sys.modules[mod]
        self._log("已卸载 %s" % name)
        return True
