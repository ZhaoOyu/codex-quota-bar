"""Background polling, with UI state delivered through a thread-safe queue."""

import queue
import threading
import time

from .client import UsageError, fetch_quota
from .model import Quota, Window, present


class Controller:
    def __init__(self, codex=None, demo=False):
        self.codex = codex
        self.demo = demo
        now = time.time()
        self.quota = Quota(Window(78, now + 9240), Window(62, now + 300000), now) if demo else None
        self.error = ""
        self.results = queue.Queue()
        self.busy = False
        self.next_poll = 0

    def refresh(self, *_):
        if self.busy or self.demo:
            return
        self.busy = True
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            self.results.put((fetch_quota(self.codex), ""))
        except UsageError as error:
            self.results.put((None, str(error)))
        except Exception:
            self.results.put((None, "读取异常；请检查 Codex 安装，稍后自动重试。"))

    def tick(self):
        now = time.time()
        try:
            quota, self.error = self.results.get_nowait()
            # Never retain a previous account's quota after a failed request.
            self.quota = quota
            self.busy = False
            self.next_poll = now + 60
        except queue.Empty:
            pass
        if now >= self.next_poll:
            self.refresh()
        return present(self.quota, now, self.error, self.demo)

