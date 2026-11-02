"""Self-check for wake_scheduler helpers. Run: python test_wake_scheduler.py"""

import sys
from datetime import datetime, timedelta

import wake_scheduler as w


def check_format():
    assert w._format_boundary("2026-11-02T23:30:00+07:00") == "02/11/2026 23:30"
    assert w._format_boundary("2026-11-02T23:30:00Z") == "02/11/2026 23:30"
    assert w._format_boundary("2026-11-02T23:30") == "02/11/2026 23:30"
    # Unparsable values are passed through untouched.
    assert w._format_boundary("garbage") == "garbage"


def check_next_occurrence():
    now = datetime.now()
    soon = (now.hour, now.minute)
    target = w.next_occurrence(soon)
    assert target >= now
    assert (target.hour, target.minute) == soon
    assert target.second == 0

    # A time already past today must land tomorrow.
    past = (now.hour - 1) % 24
    target = w.next_occurrence((past, now.minute))
    assert target > now
    assert target - now <= timedelta(days=1)


def check_app_command():
    executable, arguments = w.app_command()
    assert executable.lower().endswith("python.exe") or executable.lower().endswith(".exe")
    assert w.WAKE_FLAG in arguments


if __name__ == "__main__":
    check_format()
    check_next_occurrence()
    check_app_command()
    print("wake_scheduler self-check OK")
    sys.exit(0)
