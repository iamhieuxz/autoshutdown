"""Schedule an automatic power-on after the machine has been shut down.

Windows exposes this through Task Scheduler: a task flagged with WakeToRun
triggers the machine's RTC alarm, so the PC boots itself at a given time.
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta

TASK_NAME = "AutoShutdown Auto Wake"

# The task runs the app with this flag so it can announce the wake-up.
WAKE_FLAG = "--woke"


def _powershell():
    """Locate a usable PowerShell executable."""
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate = os.path.join(
        system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"
    )
    if os.path.isfile(candidate):
        return candidate
    return "powershell.exe"


def _run_powershell(script, timeout=30):
    return subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=timeout,
    )


def app_command():
    """Return the (executable, arguments) used to relaunch this application."""
    if getattr(sys, "frozen", False):
        return sys.executable, WAKE_FLAG
    # No quotes: PowerShell script will quote the entire argument string.
    return sys.executable, f'{os.path.abspath(sys.argv[0])} {WAKE_FLAG}'


def next_occurrence(clock_time):
    """Return the next datetime matching a (hour, minute) clock time."""
    now = datetime.now()
    target = now.replace(
        hour=clock_time[0], minute=clock_time[1], second=0, microsecond=0
    )
    if target <= now:
        target += timedelta(days=1)
    return target


def schedule_wake(hour, minute):
    """Register a wake-up task for the next occurrence of the given time.

    Returns (success, message).
    """
    when = next_occurrence((hour, minute))
    executable, arguments = app_command()

    # Interactive is deliberate: the RTC alarm is armed either way, but only
    # this logon type starts the app in the user's own session, so the tray
    # icon and the "machine woke up" notice are actually visible.
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        f"$action = New-ScheduledTaskAction -Execute '{_ps_quote(executable)}' "
        f"-Argument '{_ps_quote(arguments)}'\n"
        "$trigger = New-ScheduledTaskTrigger -Once -At "
        f"'{when.strftime('%Y-%m-%dT%H:%M:%S')}'\n"
        "$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable "
        "-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit (New-TimeSpan -Minutes 5)\n"
        "$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME "
        "-LogonType Interactive -RunLevel Highest\n"
        f"Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $action "
        "-Trigger $trigger -Settings $settings -Principal $principal "
        "-Force | Out-Null\n"
        "Write-Output 'OK'\n"
    )

    try:
        result = _run_powershell(script, timeout=45)
    except (subprocess.SubprocessError, OSError) as error:
        return False, f"Khong the chay PowerShell: {error}"

    if "OK" in result.stdout:
        return True, when.strftime("%d/%m/%Y %H:%M")
    detail = (result.stderr or result.stdout or "").strip().splitlines()
    message = detail[-1] if detail else "Khong ro nguyen nhan"
    return False, message


def _ps_quote(text):
    """Escape a value for a single-quoted PowerShell string."""
    return text.replace("'", "''")


def wake_timer_armed():
    """Return True when Windows has actually armed an RTC wake timer.

    A task can be registered and still never wake the machine, so the UI
    reports this instead of claiming success.
    """
    try:
        result = subprocess.run(
            ["powercfg", "/waketimers"], capture_output=True, text=True, timeout=15
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return TASK_NAME in result.stdout


def cancel_wake():
    """Remove the wake-up task if it exists. Returns True when removed."""
    script = (
        f"$task = Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue; "
        f"if ($task) {{ Unregister-ScheduledTask -TaskName '{TASK_NAME}' "
        "-Confirm:$false; Write-Output 'REMOVED' }"
    )
    try:
        result = _run_powershell(script, timeout=25)
    except (subprocess.SubprocessError, OSError):
        return False
    return "REMOVED" in result.stdout


def get_wake_info():
    """Return the scheduled wake time as a formatted string, or None."""
    script = (
        f"$t = Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue; "
        "if ($t) { $t.Triggers | Select-Object -First 1 -ExpandProperty StartBoundary }"
    )
    try:
        result = _run_powershell(script, timeout=20)
    except (subprocess.SubprocessError, OSError):
        return None
    value = result.stdout.strip()
    if not value:
        return None
    return _format_boundary(value)


def _format_boundary(value):
    """Turn a Task Scheduler StartBoundary into a readable local time."""
    from datetime import datetime

    # Handle both positive and negative timezone offsets: +07:00 or -05:00
    text = value.split("+")[0].split("-")[0].rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return value
