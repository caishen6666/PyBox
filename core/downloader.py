# -*- coding: utf-8 -*-
"""通用文件下载器（线程版，支持进度回调与取消）"""
import os
import threading
import urllib.request
import urllib.error


class Downloader:
    """在后台线程下载文件，通过回调通知进度。

    callbacks:
        on_progress(received, total)   # total 可能为 -1（服务器未返回长度）
        on_done(path)
        on_error(message)
    """

    def __init__(self, on_progress=None, on_done=None, on_error=None):
        self.on_progress = on_progress
        self.on_done = on_done
        self.on_error = on_error
        self._cancel = threading.Event()
        self._thread = None

    def cancel(self):
        self._cancel.set()

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, url, save_path, chunk=64 * 1024):
        """启动下载线程。"""
        if self.running:
            if self.on_error:
                self.on_error("已有任务正在下载中")
            return
        self._cancel.clear()
        self._thread = threading.Thread(
            target=self._run, args=(url, save_path, chunk), daemon=True)
        self._thread.start()

    def _safe(self, cb, *args):
        if cb:
            try:
                cb(*args)
            except Exception:
                pass

    def _run(self, url, save_path, chunk):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            tmp_path = save_path + ".part"
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (PyBox/1.0)"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(tmp_path, "wb") as f:
                total = int(resp.headers.get("Content-Length", -1) or -1)
                received = 0
                while True:
                    if self._cancel.is_set():
                        f.close()
                        os.remove(tmp_path)
                        self._safe(self.on_error, "下载已取消")
                        return
                    data = resp.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    received += len(data)
                    self._safe(self.on_progress, received, total)
            os.replace(tmp_path, save_path)
            self._safe(self.on_done, save_path)
        except urllib.error.HTTPError as e:
            self._safe(self.on_error, "HTTP 错误: %s %s" % (e.code, e.reason))
        except Exception as e:
            if os.path.exists(save_path + ".part"):
                try:
                    os.remove(save_path + ".part")
                except OSError:
                    pass
            self._safe(self.on_error, "下载失败: %s" % e)
