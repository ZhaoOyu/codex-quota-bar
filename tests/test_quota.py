import unittest

from codex_quota_bar.model import Window, countdown, parse_quota, present, remaining_text


def window(used=22, duration=300, reset=10000):
    return {"usedPercent": used, "windowDurationMins": duration, "resetsAt": reset}


class QuotaTests(unittest.TestCase):
    def parse(self, primary=None, secondary=None):
        return parse_quota({"rateLimits": {"primary": primary, "secondary": secondary}}, 1000)

    def test_remaining_not_used(self):
        quota = self.parse(window(), window(38, 10080))
        self.assertEqual(quota.five_hour.remaining, 78)
        self.assertEqual(quota.weekly.remaining, 62)

    def test_swapped_windows(self):
        quota = self.parse(window(38, 10080), window())
        self.assertEqual(quota.five_hour.remaining, 78)

    def test_missing_week_is_unknown(self):
        quota = self.parse(window())
        self.assertIsNone(quota.weekly)
        self.assertIn("W --", present(quota, 1001)[0])

    def test_unknown_duration_not_mislabeled(self):
        with self.assertRaises(ValueError):
            self.parse(window(duration=15))

    def test_codex_bucket_selected(self):
        quota = parse_quota({"rateLimits": {"primary": window(99)},
                             "rateLimitsByLimitId": {"codex": {"primary": window(10)}}}, 1000)
        self.assertEqual(quota.five_hour.remaining, 90)

    def test_other_bucket_rejected(self):
        with self.assertRaises(ValueError):
            parse_quota({"rateLimits": {"limitId": "other", "primary": window()}}, 1000)

    def test_bad_data_not_full_quota(self):
        for value in (None, "25", True, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parse(window(used=value))

    def test_clamp_usage(self):
        self.assertEqual(self.parse(window(150)).five_hour.remaining, 0)
        self.assertEqual(self.parse(window(-10)).five_hour.remaining, 100)

    def test_fractional_remaining_not_rounded_up(self):
        self.assertEqual(remaining_text(Window(99.8, None), 1000), "99%")

    def test_countdown_rounds_up(self):
        self.assertEqual(countdown(Window(78, 1021), 1000), "00:01")
        self.assertEqual(countdown(Window(78, 10240), 1000), "02:34")

    def test_expired_window_never_assumed_reset(self):
        quota = self.parse(window(reset=1000))
        self.assertEqual(remaining_text(quota.five_hour, 1000), "待刷新")
        self.assertEqual(countdown(quota.five_hour, 1000), "待刷新")

    def test_null_reset(self):
        quota = self.parse(window(reset=None))
        self.assertEqual(countdown(quota.five_hour, 1000), "--:--")

    def test_stale_and_error_are_visible(self):
        quota = self.parse(window())
        self.assertTrue(present(quota, 1200)[0].startswith("! "))
        self.assertTrue(present(quota, 1001, "offline")[0].startswith("! "))
        self.assertIn("offline", present(None, 1001, "offline")[1])

    def test_demo_labeled(self):
        self.assertTrue(present(self.parse(window()), 1000, demo=True)[0].startswith("[演示]"))


if __name__ == "__main__":
    unittest.main()

