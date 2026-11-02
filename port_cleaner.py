"""Utilities to inspect and release network ports that are currently bound."""

import os
import subprocess
import sys
from dataclasses import dataclass, field

# Processes that must never be terminated: terminating them breaks Windows.
PROTECTED_NAMES = {
    "system",
    "idle",
    "registry",
    "memory compression",
    "csrss.exe",
    "wininit.exe",
    "winlogon.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "dwm.exe",
    "fontdrvhost.exe",
    "sihost.exe",
    "ctfmon.exe",
    "spoolsv.exe",
    "audiodg.exe",
    "conhost.exe",
    "wmiprvse.exe",
    "msmpeng.exe",
    "searchindexer.exe",
    "searchprotocolhost.exe",
    "securityhealthservice.exe",
    "smartscreen.exe",
    "textinputhost.exe",
    "runtimebroker.exe",
    "systemsettings.exe",
}

# Anything living inside the Windows directory is considered part of the OS.
PROTECTED_PATH_PREFIXES = (
    os.environ.get("SystemRoot", r"C:\Windows").lower(),
    os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "system32").lower(),
)

# Well-known ports handled by kernel drivers / http.sys - not user processes.
PROTECTED_PORTS = {135, 137, 138, 139, 445, 5985, 5986, 47001}


@dataclass
class PortEntry:
    pid: int
    port: int
    protocol: str
    process_name: str = "?"
    exe_path: str = ""
    protected: bool = False
    reasons: list = field(default_factory=list)

    @property
    def label(self):
        return f"{self.process_name} (PID {self.pid})"


def _run(command):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",  # keep trace of decoding errors
    )


def _process_name_map():
    """Map of pid -> image name using a single tasklist call."""
    result = _run(["tasklist", "/FO", "CSV", "/NH"])
    names = {}
    for line in result.stdout.splitlines():
        parts = [part.strip().strip('"') for part in line.split('","')]
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[1])
        except ValueError:
            continue
        names[pid] = parts[0]
    return names


def _exe_path_map():
    """Map of pid -> executable path using psutil when available."""
    try:
        import psutil
    except ImportError:
        return {}
    paths = {}
    for process in psutil.process_iter(["pid", "exe"]):
        try:
            paths[process.info["pid"]] = process.info.get("exe") or ""
        except Exception:
            continue
    return paths


def _is_protected(entry: PortEntry):
    reasons = []
    if entry.pid <= 4:
        reasons.append("tiến trình hệ thống")
    if entry.process_name.lower() in PROTECTED_NAMES:
        reasons.append("tiến trình hệ thống")
    if entry.exe_path:
        lowered = entry.exe_path.lower()
        if any(lowered.startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES):
            reasons.append("nằm trong thư mục Windows")
    if entry.port in PROTECTED_PORTS:
        reasons.append("cổng hệ thống")
    entry.reasons = reasons
    entry.protected = bool(reasons)
    return entry.protected


def list_bound_ports():
    """Return every TCP listening and UDP bound port with its owning process."""
    result = _run(["netstat", "-ano"])
    names = _process_name_map()
    paths = _exe_path_map()

    entries = []
    seen = set()

    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        protocol = parts[0].upper()
        if protocol not in ("TCP", "UDP"):
            continue

        local = parts[1]
        if ":" not in local:
            continue
        try:
            port = int(local.rsplit(":", 1)[1])
        except ValueError:
            continue

        if protocol == "TCP":
            state = parts[3].upper() if len(parts) > 3 else ""
            if state != "LISTENING":
                continue

        try:
            pid = int(parts[-1])
        except ValueError:
            continue

        key = (protocol, port, pid)
        if key in seen:
            continue
        seen.add(key)

        entry = PortEntry(
            pid=pid,
            port=port,
            protocol=protocol,
            process_name=names.get(pid, f"PID {pid}"),
            exe_path=paths.get(pid, ""),
        )
        _is_protected(entry)
        entries.append(entry)

    entries.sort(key=lambda item: (item.protocol, item.port))
    return entries


def terminate(pid: int) -> bool:
    """Force kill a process and its children."""
    result = _run(["taskkill", "/F", "/T", "/PID", str(pid)])
    return result.returncode == 0


def release_ports(entries):
    """Terminate every unprotected entry, returning (killed, failed) lists."""
    killed = []
    failed = []
    for entry in entries:
        if entry.protected:
            continue
        if terminate(entry.pid):
            killed.append(entry)
        else:
            failed.append(entry)
    return killed, failed
