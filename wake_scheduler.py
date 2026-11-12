"""Schedule an automatic power-on after the machine has been shut down.

Windows exposes this through Task Scheduler: a task flagged with WakeToRun
triggers the machine's RTC alarm, so the PC boots itself at a given time.
"""

import base64
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

TASK_NAME = "AutoShutdown Auto Wake"

# The task runs the app with this flag so it can announce the wake-up.
WAKE_FLAG = "--woke"

# A windowed build has no console, so every console child would flash a cmd
# window without this flag.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


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
    # Force UTF-8 on stdout: PowerShell 5.1 otherwise writes the console code
    # page, which does not match the decoding below. Guarded because a build
    # that runs without any console must not fail on this line.
    script = (
        "try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }\n"
        + script
    )
    
    # Retry once if PowerShell fails (in case it restarted)
    for attempt in range(2):
        try:
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
                errors="replace",
                timeout=timeout,
                creationflags=_NO_WINDOW,
            )
        except (subprocess.SubprocessError, OSError) as e:
            if attempt == 0:
                # First attempt failed, retry once
                continue
            # Second attempt failed
            return None


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


def task_state():
    """Return {"boundary", "wake_to_run"} for the registered task, or None.

    One call answers both "is a task registered" and "will it wake the
    machine", because a task without the WakeToRun flag never powers the PC on.
    """
    script = (
        "$ErrorActionPreference = 'SilentlyContinue'\n"
        f"$t = Get-ScheduledTask -TaskName '{TASK_NAME}'\n"
        "if (-not $t) { return }\n"
        "[pscustomobject]@{\n"
        "  boundary = ($t.Triggers | Select-Object -First 1).StartBoundary\n"
        "  wake_to_run = [bool]$t.Settings.WakeToRun\n"
        "} | ConvertTo-Json -Compress\n"
    )
    result = _run_powershell(script, timeout=20)
    if result is None:
        return None
    text = (result.stdout or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    
    # Validate required keys exist
    if "boundary" not in data or "wake_to_run" not in data:
        return None
    
    return {
        "boundary": str(data.get("boundary") or ""),
        "wake_to_run": bool(data.get("wake_to_run")),
    }


def schedule_wake(hour, minute):
    """Register a wake-up task for the next occurrence of the given time.

    Returns (success, message).
    """
    when = next_occurrence((hour, minute))
    executable, arguments = app_command()

    # Interactive is deliberate: the RTC alarm is armed either way, but only
    # this logon type starts the app in the user's own session, so the tray
    # icon and the "machine woke up" notice are actually visible. Limited
    # integrity keeps registration working without an elevated prompt; the
    # task only has to show a notification.
    
    # Encode exe and args as base64 to avoid PowerShell injection
    exe_b64 = base64.b64encode(executable.encode('utf-8')).decode('ascii')
    args_b64 = base64.b64encode(arguments.encode('utf-8')).decode('ascii')
    
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        f"$exe = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{exe_b64}'))\n"
        f"$args = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{args_b64}'))\n"
        "$action = New-ScheduledTaskAction -Execute $exe -Argument $args\n"
        "$trigger = New-ScheduledTaskTrigger -Once -At "
        f"'{when.strftime('%Y-%m-%dT%H:%M:%S')}'\n"
        "$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable "
        "-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit (New-TimeSpan -Minutes 5)\n"
        "$principal = New-ScheduledTaskPrincipal -UserId "
        "([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) "
        "-LogonType Interactive -RunLevel Limited\n"
        f"Register-ScheduledTask -TaskName '{_ps_quote(TASK_NAME)}' -Action $action "
        "-Trigger $trigger -Settings $settings -Principal $principal "
        "-Force | Out-Null\n"
        "Write-Output 'OK'\n"
    )

    result = _run_powershell(script, timeout=45)
    if result is None:
        return False, "Không chạy được PowerShell."

    if "OK" in result.stdout:
        return True, when.strftime("%d/%m/%Y %H:%M")
    detail = (result.stderr or result.stdout or "").strip().splitlines()
    message = detail[-1] if detail else "Không rõ nguyên nhân"
    return False, message


def _ps_quote(text):
    """Escape a value for a single-quoted PowerShell string."""
    return text.replace("'", "''")


def _parse_boundary(value):
    """Parse a Task Scheduler StartBoundary into a local datetime, or None."""
    # fromisoformat handles +07:00 / -05:00; "Z" is only a Python 3.11 spelling.
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        # Convert to naive local time for consistent comparison
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except ValueError:
        return None


def wake_info():
    """Return {"time", "armed"} for a wake that can still happen, else None.

    A one-time task stays registered after it fires, so a past StartBoundary
    must not be reported as an upcoming wake.
    """
    state = task_state()
    if not state or not state["boundary"]:
        return None
    when = _parse_boundary(state["boundary"])
    if when is None or when <= datetime.now():
        return None
    return {"time": _format_boundary(state["boundary"]), "armed": state["wake_to_run"]}


def cancel_wake():
    """Remove the wake-up task if it exists. Returns True when removed."""
    script = (
        f"$task = Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue; "
        f"if ($task) {{ Unregister-ScheduledTask -TaskName '{TASK_NAME}' "
        "-Confirm:$false; Write-Output 'REMOVED' }"
    )
    result = _run_powershell(script, timeout=25)
    if result is None:
        return False
    return "REMOVED" in result.stdout


def _format_boundary(value):
    """Turn a Task Scheduler StartBoundary into a readable local time."""
    when = _parse_boundary(value)
    if when is None:
        return value
    return when.strftime("%d/%m/%Y %H:%M")
