"""Utilities to inspect and release network ports that are currently bound."""

import logging
import os
import subprocess
from dataclasses import dataclass, field

# A windowed build has no console, so every console child would flash a cmd
# window without this flag.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

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
PROTECTED_PATH_PREFIXES = (os.environ.get("SystemRoot", r"C:\Windows").lower(),)

# Well-known ports handled by kernel drivers / http.sys - not user processes.
# 53 is DNS: closing the resolver takes the whole network down.
PROTECTED_PORTS = {53, 135, 137, 138, 139, 445, 5985, 5986, 47001}


@dataclass
class PortEntry:
    pid: int
    port: int
    protocol: str
    process_name: str = "?"
    exe_path: str = ""
    known_name: bool = True
    protected: bool = False
    reasons: list = field(default_factory=list)

    @property
    def label(self):
        return f"{self.process_name} (PID {self.pid})"


def _run(command, timeout=20):
    """Run a console command quietly. Returns None when it cannot run at all."""
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # keep trace of decoding errors
            timeout=timeout,
            creationflags=_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        logging.warning(f"Command {command[0]} timed out after {timeout}s")
        return None
    except (OSError, subprocess.SubprocessError) as e:
        logging.warning(f"Cannot run {command[0]}: {e}")
        return None


def _stdout(result):
    return result.stdout if result is not None else ""


def parse_tasklist(text):
    """Map pid -> image name from `tasklist /FO CSV /NH` output."""
    names = {}
    for line in text.splitlines():
        parts = [part.strip().strip('"') for part in line.split('","')]
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[1])
        except ValueError:
            continue
        if parts[0]:
            names[pid] = parts[0]
    return names


def _process_info_map():
    """Return (pid -> name, pid -> exe path), merging tasklist and psutil.

    psutil is the only source for the executable path needed by the
    Windows-directory guard, and its name is the fallback when tasklist cannot
    see a pid (otherwise such a process would look unprotected).
    """
    names = parse_tasklist(_stdout(_run(["tasklist", "/FO", "CSV", "/NH"])))
    paths = {}
    
    try:
        import psutil
        has_psutil = True
    except ImportError:
        has_psutil = False
    
    if not has_psutil:
        return names, paths
    
    try:
        for process in psutil.process_iter(["pid", "name", "exe"]):
            try:
                info = process.info
                pid = info.get("pid")
                if pid is None:
                    continue
                paths[pid] = info.get("exe") or ""
                name = info.get("name")
                if name and pid not in names:
                    names[pid] = name
            except Exception:
                continue
    except Exception:
        # psutil.process_iter() can fail if processes are being killed/created rapidly
        pass
    
    return names, paths


def parse_netstat(text):
    """Return (protocol, port, pid) for TCP listeners and UDP bound ports."""
    rows = []
    seen = set()
    for line in text.splitlines():
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

        # TCP rows: proto, local, foreign, state, pid. A listener is the row
        # whose peer port is 0: the state word is localized on a non-English
        # Windows (and printed in the OEM code page), so it cannot be matched.
        if protocol == "TCP":
            if len(parts) < 5:
                continue
            foreign = parts[2]
            peer_port = foreign.rsplit(":", 1)[1] if ":" in foreign else ""
            if peer_port != "0" and parts[3].upper() != "LISTENING":
                continue

        try:
            pid = int(parts[-1])
        except ValueError:
            continue

        key = (protocol, port, pid)
        if key in seen:
            continue
        seen.add(key)
        rows.append((protocol, port, pid))
    return rows


def _is_protected(entry: PortEntry):
    """Decide whether a port's process must be left alone.

    Fails closed: an entry whose process could not be identified counts as
    protected, because killing an unknown SYSTEM process breaks Windows.
    """
    reasons = []

    def add(reason):
        if reason not in reasons:
            reasons.append(reason)

    if entry.pid <= 4:
        add("tiến trình hệ thống")
    if entry.process_name.lower() in PROTECTED_NAMES:
        add("tiến trình hệ thống")
    if not entry.known_name:
        add("không xác định được tiến trình")
    if entry.exe_path:
        lowered = entry.exe_path.lower()
        if any(lowered.startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES):
            add("nằm trong thư mục Windows")
    if entry.port in PROTECTED_PORTS:
        add("cổng hệ thống")
    entry.reasons = reasons
    entry.protected = bool(reasons)
    return entry.protected


def list_bound_ports():
    """Return every TCP listening and UDP bound port with its owning process."""
    names, paths = _process_info_map()

    entries = []
    for protocol, port, pid in parse_netstat(_stdout(_run(["netstat", "-ano"]))):
        name = names.get(pid)
        entry = PortEntry(
            pid=pid,
            port=port,
            protocol=protocol,
            process_name=name or f"PID {pid}",
            exe_path=paths.get(pid, ""),
            known_name=name is not None,
        )
        _is_protected(entry)
        entries.append(entry)

    entries.sort(key=lambda item: (item.protocol, item.port))
    return entries


def terminate(pid: int) -> bool:
    """Force kill a process and its children."""
    result = _run(["taskkill", "/F", "/T", "/PID", str(pid)])
    if result is None:
        return False
    # 128 = process not found: it is already gone, which is what we wanted.
    return result.returncode in (0, 128)


def release_ports(entries):
    """Terminate every unprotected entry, returning (killed, failed) lists.

    One process can own several ports, so the list is grouped by pid: without
    that, every second port would run taskkill against a pid that is already
    dead and be reported as a failure.
    """
    groups = {}
    order = []
    protected_pids = {entry.pid for entry in entries if entry.protected}
    for entry in entries:
        if entry.protected:
            continue
        if entry.pid not in groups:
            groups[entry.pid] = []
            order.append(entry.pid)
        groups[entry.pid].append(entry)

    killed = []
    failed = []
    for pid in order:
        group = groups[pid]
        # Protection wins per process: killing it would take a protected port
        # down with it, so the whole group stays.
        if pid in protected_pids or not terminate(pid):
            failed.extend(group)
        else:
            killed.extend(group)
    return killed, failed
