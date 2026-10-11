# -*- coding: utf-8 -*-
"""迷你代码运行器：在独立线程中执行用户代码并捕获输出。"""
import io
import threading
import traceback
from contextlib import redirect_stdout, redirect_stderr


class CodeRunner:
    def __init__(self, on_output=None, on_finish=None):
        self.on_output = on_output
        self.on_finish = on_finish
        self._thread = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def run(self, code, timeout=30):
        if self.running:
            if self.on_output:
                self.on_output("[!] 已有代码正在运行\n")
            return
        self._thread = threading.Thread(
            target=self._run, args=(code, timeout), daemon=True)
        self._thread.start()

    def _run(self, code, timeout):
        buf = io.StringIO()
        env = {"__name__": "__pybox__"}
        watcher = threading.Timer(timeout, self._timeout)
        watcher.daemon = True
        try:
            watcher.start()
            with redirect_stdout(buf), redirect_stderr(buf):
                exec(compile(code, "<PyBox>", "exec"), env)   # noqa: S102 - 沙盒演示
            watcher.cancel()
            out = buf.getvalue()
            if self.on_output and out:
                self.on_output(out)
            if self.on_finish:
                self.on_finish(True, "")
        except Exception:
            watcher.cancel()
            err = traceback.format_exc(limit=4)
            if self.on_output:
                self.on_output(buf.getvalue() + "\n" + err)
            if self.on_finish:
                self.on_finish(False, err)
        finally:
            watcher.cancel()

    def _timeout(self):
        # 超时只能粗暴提示；线程本身通过 daemon 结束时清理
        if self.on_output:
            self.on_output("\n[!] 运行超过时限（%s 秒），结果可能不完整\n")
