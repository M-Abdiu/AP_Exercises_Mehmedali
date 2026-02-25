import unittest
import tempfile
import io
import contextlib
from pathlib import Path

from timer_app.domain.errors import ValidationError
from timer_app.ui import cli


class TestCliDurationParsing(unittest.TestCase):
    def test_parse_duration_seconds_accepts_basic_forms(self):
        self.assertEqual(cli._parse_duration_seconds("5"), 5)
        self.assertEqual(cli._parse_duration_seconds("0:05"), 5)
        self.assertEqual(cli._parse_duration_seconds("1:00"), 60)
        self.assertEqual(cli._parse_duration_seconds("1:02:03"), 3723)

    def test_parse_duration_seconds_rejects_negative(self):
        with self.assertRaises(ValidationError):
            cli._parse_duration_seconds("-1")

    def test_parse_duration_seconds_rejects_out_of_range_seconds(self):
        with self.assertRaises(ValidationError):
            cli._parse_duration_seconds("0:60")

    def test_parse_duration_seconds_rejects_out_of_range_minutes_seconds(self):
        with self.assertRaises(ValidationError):
            cli._parse_duration_seconds("1:60:00")

    def test_parse_duration_seconds_rejects_too_many_fields(self):
        with self.assertRaises(ValidationError):
            cli._parse_duration_seconds("1:2:3:4")

    def test_countdown_duration_zero_returns_exit_2(self):
        # main() catches ValidationError and returns 2.
        with tempfile.TemporaryDirectory() as td:
            store_path = Path(td) / "state.json"
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = cli.main(["--store", str(store_path), "countdown", "0"])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
