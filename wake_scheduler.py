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
    """Return the command used to relaunch this application."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" {WAKE_FLAG}'
    script = os.path.abspath(sys.argv[0])
    return f'"{sys.executable}" "{script}" {WAKE_FLAG}'


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
    action = app_command()

    script = (
        "$ErrorActionPreference = 'Stop'\n"
        f"$action = New-ScheduledTaskAction -Execute 'cmd.exe' "
        f"-Argument '/c {action}'\n"
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
    return value or None
