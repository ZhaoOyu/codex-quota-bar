import unittest
from unittest.mock import patch

from codex_quota_bar.controller import Controller
from codex_quota_bar.model import Quota, Window


class ControllerTests(unittest.TestCase):
    def test_error_clears_previous_account_quota_and_recovers(self):
        controller = Controller()
        controller.quota = Quota(Window(90, 2000), None, 1000)
        controller.results.put((None, "登录失败"))
        with patch("codex_quota_bar.controller.time.time", return_value=1001):
            title, _ = controller.tick()
        self.assertIsNone(controller.quota)
        self.assertEqual(title, "Codex !")
        controller.results.put((Quota(Window(50, 3000), None, 1100), ""))
        with patch("codex_quota_bar.controller.time.time", return_value=1101):
            title, _ = controller.tick()
        self.assertIn("5h 50%", title)

    def test_polls_are_not_overlapped(self):
        controller = Controller()
        controller.busy = True
        with patch("codex_quota_bar.controller.threading.Thread") as thread:
            controller.refresh()
            thread.assert_not_called()

    def test_demo_does_not_contact_server(self):
        controller = Controller(demo=True)
        with patch("codex_quota_bar.controller.threading.Thread") as thread:
            controller.tick()
            thread.assert_not_called()

