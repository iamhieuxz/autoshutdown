"""Self-check for wake_scheduler helpers. Run: python test_wake_scheduler.py"""

import json
import sys
from datetime import datetime, timedelta

import wake_scheduler as w


def test_format():
    # Test with timezone offset: +07:00 time should be returned as-is (local)
    result = w._format_boundary("2026-11-02T23:30:00+07:00")
    assert result == "02/11/2026 23:30", result
    
    # Test with naive timestamp: should return as-is
    result = w._format_boundary("2026-11-02T23:30")
    assert result == "02/11/2026 23:30", result
    
    # Unparsable values are passed through untouched.
    assert w._format_boundary("garbage") == "garbage"


def test_next_occurrence():
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


def test_app_command():
    executable, arguments = w.app_command()
    assert executable.lower().endswith("python.exe") or executable.lower().endswith(".exe")
    assert w.WAKE_FLAG in arguments


class FakeResult:
    def __init__(self, stdout):
        self.returncode = 0
        self.stdout = stdout
        self.stderr = ""


def with_powershell(result, check):
    """Run `check` with PowerShell stubbed out, so no real task is touched."""
    captured = {}

    def fake(script, timeout=30):
        captured["script"] = script
        return result

    original = w._run_powershell
    w._run_powershell = fake
    try:
        check(captured)
    finally:
        w._run_powershell = original


def future_boundary(hours=3):
    return (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")


def task_payload(boundary, wake_to_run=True):
    return json.dumps({"boundary": boundary, "wake_to_run": wake_to_run})


def test_task_state_reads_wake_flag():
    boundary = future_boundary()

    def armed(captured):
        state = w.task_state()
        assert state == {"boundary": boundary, "wake_to_run": True}, state
        assert w.wake_info()["armed"] is True
        assert "WakeToRun" in captured["script"], captured["script"]

    with_powershell(FakeResult(task_payload(boundary, True)), armed)

    def not_armed(captured):
        assert w.wake_info()["armed"] is False

    with_powershell(FakeResult(task_payload(boundary, False)), not_armed)


def test_wake_info_ignores_a_fired_task():
    # Task Scheduler keeps a one-time task after it fires (past StartBoundary).
    past = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    with_powershell(
        FakeResult(task_payload(past, True)), lambda captured: _assert_none(w.wake_info())
    )

    boundary = future_boundary()

    def upcoming(captured):
        info = w.wake_info()
        assert info is not None, info
        assert info["armed"] is True, info
        assert boundary[11:16] in info["time"], info

    with_powershell(FakeResult(task_payload(boundary, True)), upcoming)


def _assert_none(value):
    assert value is None, value


def test_task_state_without_task():
    def check(captured):
        assert w.task_state() is None
        assert w.wake_info() is None

    with_powershell(FakeResult(""), check)
    with_powershell(FakeResult("not json"), check)


def test_schedule_wake_registers_an_unprivileged_interactive_task():
    def check(captured):
        success, message = w.schedule_wake(6, 30)
        assert success is True, message
        script = captured["script"]
        # The elevation-free path and the domain-qualified identity are the
        # whole point of the registration change.
        assert "-RunLevel Limited" in script, script
        assert "WindowsIdentity]::GetCurrent().Name" in script, script
        assert "-LogonType Interactive" in script, script
        assert "-WakeToRun" in script, script
        assert "Register-ScheduledTask" in script, script
        # The script is piped as one -Command argument; quoting must survive.
        assert "$env:USERNAME" not in script, script

    with_powershell(FakeResult("OK"), check)


def test_powershell_unavailable_is_reported_not_raised():
    with_powershell(None, lambda captured: _assert_none(w.task_state()))
    with_powershell(None, lambda captured: _assert_none(w.wake_info()))

    def schedule(captured):
        success, message = w.schedule_wake(6, 30)
        assert success is False
        assert "PowerShell" in message, message

    with_powershell(None, schedule)
    with_powershell(None, lambda captured: _assert_false(w.cancel_wake()))


def _assert_false(value):
    assert value is False, value


if __name__ == "__main__":
    test_format()
    test_next_occurrence()
    test_app_command()
    test_task_state_reads_wake_flag()
    test_wake_info_ignores_a_fired_task()
    test_task_state_without_task()
    test_schedule_wake_registers_an_unprivileged_interactive_task()
    test_powershell_unavailable_is_reported_not_raised()
    print("wake_scheduler self-check OK")
    sys.exit(0)
