# -*- coding: utf-8 -*-
"""PyBox —— 带界面的 Python 工具箱 App

功能：
  1. 文件下载（URL → 本地，进度条/取消）
  2. PyPI 库管理（运行时下载并安装纯 Python 包，立即 import 可用）
  3. 迷你代码运行器（写 Python，立即执行并查看输出）

桌面端直接运行:  python main.py
安卓端用 buildozer 打包成 APK（见 README.md）
"""
import os
import sys

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.textinput import TextInput

# 捆绑的中文字体（assets/NotoSansSC.ttf，GB2312+ASCII 裁剪版）
_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "NotoSansSC.ttf")
if os.path.exists(_FONT):
    _fp = _FONT.replace("\\", "/")
    Builder.load_string(
        "<Label>:\n    font_name: '%s'\n"
        "<TextInput>:\n    font_name: '%s'" % (_fp, _fp))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.downloader import Downloader            # noqa: E402
from core.pypi_manager import PyPIManager         # noqa: E402
from core.code_runner import CodeRunner           # noqa: E402

DEMO_CODE = """\
# 在这里写 Python 代码，点「运行」执行
# 先去「装库」页安装一个纯 Python 包（例如 six 或 humanize），
# 然后就可以在这里 import 它们！

import sys, platform
print("Python:", sys.version.split()[0])
print("平台:", platform.platform())

try:
    import six
    print("six 库工作正常, __version__ =", six.__version__)
except ImportError:
    print("six 尚未安装，去「装库」页试试吧")
"""


class TabDownload(BoxLayout):
    """下载页：URL 输入 + 进度条 + 状态。"""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(10), **kw)
        self.app = App.get_running_app()

        self.add_widget(Label(text="文件下载器", font_size=sp(22), size_hint_y=None, height=dp(36)))
        self.url_input = TextInput(
            text="https://pypi.org/pypi/json", multiline=False,
            hint_text="输入要下载的文件 URL",
            size_hint_y=None, height=dp(40))
        self.add_widget(self.url_input)

        self.bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(18))
        self.add_widget(self.bar)
        self.status = Label(
            text="就绪  |  保存到: %s" % self.app.download_dir,
            font_size=sp(13), size_hint_y=None, height=dp(40),
            text_size=(None, None), halign="left", shorten=True)
        self.status.bind(size=lambda w, s: setattr(w, "text_size", s))
        self.add_widget(self.status)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_dl = Button(text="开始下载", background_normal="",
                        background_color=(0.18, 0.55, 0.34, 1))
        btn_cancel = Button(text="取消", background_normal="",
                            background_color=(0.75, 0.35, 0.25, 1))
        btn_dl.bind(on_press=self.start)
        btn_cancel.bind(on_press=self.cancel)
        row.add_widget(btn_dl)
        row.add_widget(btn_cancel)
        self.add_widget(row)
        self.add_widget(Label(size_hint_y=None, height=dp(6)))

        self._dl = Downloader(on_progress=self._on_progress,
                              on_done=self._on_done,
                              on_error=self._on_error)

    # ---- 线程回调 → 主线程 UI ----
    def _ui(self, fn):
        Clock.schedule_once(lambda dt: fn())

    def _on_progress(self, received, total):
        def upd():
            if total > 0:
                self.bar.value = received * 100.0 / total
                self.status.text = "下载中 %.1f / %.1f MB (%.0f%%)" % (
                    received / 1048576.0, total / 1048576.0, self.bar.value)
            else:
                self.status.text = "下载中 %.1f MB（大小未知）" % (received / 1048576.0)
        self._ui(upd)

    def _on_done(self, path):
        def upd():
            self.bar.value = 100
            self.status.text = "完成 → %s" % path
        self._ui(upd)

    def _on_error(self, msg):
        self._ui(lambda: setattr(self.status, "text", "出错: %s" % msg))

    # ---- 按钮事件 ----
    def start(self, *_):
        url = self.url_input.text.strip()
        if not url:
            self.status.text = "请输入 URL"
            return
        self.bar.value = 0
        self.status.text = "连接中 ..."
        name = os.path.basename(url.split("?")[0]) or "download.bin"
        self._dl.start(url, os.path.join(self.app.download_dir, name))

    def cancel(self, *_):
        self._dl.cancel()
        self.status.text = "正在取消 ..."


class TabPackages(BoxLayout):
    """装库页：输入包名 → 从 PyPI 下载纯 Python 包安装到私有 site-packages。"""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(10), **kw)
        self.app = App.get_running_app()

        self.add_widget(Label(text="PyPI 库管理", font_size=sp(22),
                              size_hint_y=None, height=dp(36)))
        self.pkg_input = TextInput(
            text="six", multiline=False, hint_text="包名，例如 six / humanize / attrs",
            size_hint_y=None, height=dp(40))
        self.add_widget(self.pkg_input)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b_install = Button(text="安装", background_normal="",
                           background_color=(0.18, 0.55, 0.34, 1))
        b_uninstall = Button(text="卸载", background_normal="",
                             background_color=(0.75, 0.35, 0.25, 1))
        b_install.bind(on_press=self.install)
        b_uninstall.bind(on_press=self.uninstall)
        row.add_widget(b_install)
        row.add_widget(b_uninstall)
        self.add_widget(row)

        self.log_scroll = ScrollView()
        self.log = Label(text="", font_size=sp(13), valign="top",
                         size_hint_y=None, text_size=(Window.width - dp(30), None))
        self.log.bind(texture_size=lambda w, s: setattr(w, "height", s[1]))
        self.log_scroll.add_widget(self.log)
        self.add_widget(self.log_scroll)

        self.list_btn = Button(text="刷新已装列表", size_hint_y=None, height=dp(40))
        self.list_btn.bind(on_press=lambda *_: self.refresh_list())
        self.add_widget(self.list_btn)

        self.mgr = PyPIManager(self.app.site_dir,
                               on_log=lambda m: Clock.schedule_once(
                                   lambda dt: self._append_log(m)),
                               on_done=lambda n, v: Clock.schedule_once(
                                   lambda dt: self.refresh_list()),
                               on_error=lambda e: None)
        self.refresh_list()

    def _append_log(self, msg):
        self.log.text += msg + "\n"
        self.log_scroll.scroll_y = 0

    def refresh_list(self):
        meta = self.mgr.installed_packages()
        if meta:
            lines = ["[已安装 %d 个包]"] % len(meta)
            for name, info in meta.items():
                lines.append("  %s==%s  (%s)" % (name, info.get("version"), info.get("kind")))
        else:
            lines = ["[尚无已安装的包，输入包名点「安装」试试]"]
        lines.append("安装位置: %s" % self.app.site_dir)
        self.log.text = "\n".join(lines) + "\n"

    def install(self, *_):
        name = self.pkg_input.text.strip()
        if not name:
            return
        self._append_log(">>> 安装 %s" % name)
        self.mgr.install(name)

    def uninstall(self, *_):
        name = self.pkg_input.text.strip()
        if not name:
            return
        ok = self.mgr.uninstall(name)
        self._append_log(">>> 卸载 %s %s" % (name, "成功" if ok else "失败"))
        self.refresh_list()


class TabRunner(BoxLayout):
    """运行页：写代码 → 执行 → 显示输出。"""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(10), **kw)
        self.add_widget(Label(text="代码运行器", font_size=sp(22),
                              size_hint_y=None, height=dp(36)))
        self.code = TextInput(text=DEMO_CODE, font_size=sp(14),
                              background_normal="", background_color=(0.97, 0.97, 0.97, 1))
        self.add_widget(self.code)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b_run = Button(text="▶ 运行", background_normal="",
                       background_color=(0.18, 0.55, 0.34, 1))
        b_clear = Button(text="清空输出", background_normal="",
                         background_color=(0.5, 0.5, 0.55, 1))
        b_run.bind(on_press=self.run)
        b_clear.bind(on_press=lambda *_: setattr(self.out, "text", ""))
        row.add_widget(b_run)
        row.add_widget(b_clear)
        self.add_widget(row)

        self.out_scroll = ScrollView(size_hint_y=None, height=dp(180))
        self.out = Label(text="(输出区)", font_size=sp(13), valign="top",
                         size_hint_y=None, text_size=(Window.width - dp(30), None))
        self.out.bind(texture_size=lambda w, s: setattr(w, "height", max(s[1], dp(160))))
        self.out_scroll.add_widget(self.out)
        self.add_widget(self.out_scroll)

        self.runner = CodeRunner(
            on_output=lambda text: Clock.schedule_once(
                lambda dt: self._show(text)),
            on_finish=lambda ok, err: Clock.schedule_once(
                lambda dt: self._show("\n[-- 运行结束 --]\n")))

    def _show(self, text):
        self.out.text += text
        self.out_scroll.scroll_y = 0

    def run(self, *_):
        self.out.text = ""
        self.runner.run(self.code.text)


class TabAbout(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", spacing=dp(6), padding=dp(16), **kw)
        app = App.get_running_app()
        self.add_widget(Label(text="PyBox v1.0", font_size=sp(26)))
        self.add_widget(Label(text="带界面的 Python 工具箱", font_size=sp(16)))
        info = (
            "· 文件下载: 输入 URL 即可下载，实时进度\n"
            "· 装库: 运行时从 PyPI 下载纯 Python 包，\n"
            "  解压到私有 site-packages 并加入 sys.path，\n"
            "  装完即可在「运行」页 import 使用\n"
            "· 运行: 内置代码运行器，捕获 stdout/stderr\n\n"
            "数据目录: %s\n"
            "Python: %s\n"
            "界面: Kivy %s" % (
                app.user_data_dir,
                sys.version.split()[0],
                __import__("kivy").__version__))
        lbl = Label(text=info, font_size=sp(14), halign="left", valign="top")
        self.add_widget(lbl)


class RootPanel(TabbedPanel):
    def __init__(self, **kw):
        super().__init__(do_default_tab=False, **kw)
        for title, cls in (("下载", TabDownload), ("装库", TabPackages),
                           ("运行", TabRunner), ("关于", TabAbout)):
            item = TabbedPanelItem(text=title)
            item.add_widget(cls())
            self.add_widget(item)


class PyBoxApp(App):
    title = "PyBox"

    def _get_user_data_dir(self):
        """数据目录：安卓用应用私有目录（无需存储权限）；
        桌面端用程序目录下的 appdata，绿色便携。"""
        from kivy.utils import platform
        if platform == "android":
            return super()._get_user_data_dir()
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "appdata")

    def build(self):
        Window.clearcolor = (0.96, 0.96, 0.94, 1)
        # 私有数据目录
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.download_dir = os.path.join(self.user_data_dir, "downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        self.site_dir = os.path.join(self.user_data_dir, "site-packages")
        return RootPanel()


if __name__ == "__main__":
    PyBoxApp().run()
