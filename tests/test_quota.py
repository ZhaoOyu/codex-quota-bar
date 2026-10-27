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

    def test_weekly_only_hides_five_hour_everywhere(self):
        for primary, secondary in ((None, window(38, 10080)), (window(38, 10080), None)):
            with self.subTest(primary=primary):
                title, rows = present(self.parse(primary, secondary), 1001)
                self.assertEqual(title, "W 62% · 02:30")
                self.assertEqual(len(rows), 3)
                self.assertFalse(any("五小时" in row for row in rows))
                self.assertTrue(rows[0].startswith("每周剩余：62%"))
                self.assertTrue(rows[1].startswith("周额度重置："))

    def test_weekly_countdown_handles_multiple_days(self):
        quota = self.parse(None, window(38, 10080, reset=1000 + 72 * 3600 + 15 * 60))
        self.assertEqual(present(quota, 1000)[0], "W 62% · 3天0小时")
        self.assertEqual(present(quota, 1060)[0], "W 62% · 3天0小时")

    def test_weekly_countdown_day_boundary(self):
        for seconds, expected in ((24 * 3600 - 61, "23:59"),
                                  (24 * 3600, "24:00"),
                                  (24 * 3600 + 1, "1天0小时"),
                                  (47 * 3600 + 3599, "1天23小时"),
                                  (48 * 3600, "2天0小时"),
                                  (75 * 3600, "3天3小时")):
            with self.subTest(seconds=seconds):
                quota = self.parse(None, window(38, 10080, 1000 + seconds))
                self.assertEqual(present(quota, 1000)[0], "W 62% · " + expected)

    def test_default_countdown_keeps_hours(self):
        self.assertEqual(countdown(Window(62, 1000 + 75 * 3600), 1000), "75:00")

    def test_weekly_countdown_missing_or_expired_reset(self):
        for reset, expected in ((None, "W 62% · --:--"), (1000, "W 待刷新 · 待刷新")):
            with self.subTest(reset=reset):
                self.assertEqual(present(self.parse(None, window(38, 10080, reset)), 1000)[0], expected)

    def test_five_hour_countdown_takes_priority(self):
        for reset, expected in ((4600, "01:00"), (None, "--:--"), (1000, "待刷新")):
            with self.subTest(reset=reset):
                quota = self.parse(window(reset=reset), window(38, 10080, 1000 + 72 * 3600))
                self.assertTrue(present(quota, 1000)[0].endswith(" · " + expected))

    def test_exhausted_five_hour_window_is_not_hidden(self):
        title, rows = present(self.parse(window(100), window(38, 10080)), 1001)
        self.assertIn("5h 0%", title)
        self.assertEqual(len(rows), 5)
        self.assertTrue(any("五小时结束" in row for row in rows))

    def test_error_and_loading_do_not_invent_windows(self):
        for error in ("", "读取失败"):
            title, rows = present(None, 1001, error)
            self.assertEqual(len(rows), 1)
            self.assertNotIn("五小时", rows[0])

    def test_window_can_disappear_and_return(self):
        both = self.parse(window(), window(38, 10080))
        weekly = self.parse(None, window(38, 10080))
        self.assertEqual([len(present(q, 1001)[1]) for q in (both, weekly, None, both)],
                         [5, 3, 1, 5])

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

