"""Self-check for the port scanning and protection logic.

Run: python test_port_cleaner.py   (pytest also collects the test_* functions)
"""

import port_cleaner


def entry(pid, port, protocol="TCP", name=None, exe="", known=True):
    return port_cleaner.PortEntry(
        pid=pid,
        port=port,
        protocol=protocol,
        process_name=name or f"app{pid}.exe",
        exe_path=exe,
        known_name=known,
    )


def test_parse_netstat():
    text = """Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       928
  TCP    192.168.1.5:8080       0.0.0.0:0              LISTENING       11520
  TCP    192.168.1.5:50000      13.107.42.14:443       ESTABLISHED     11520
  TCP    [::]:135               [::]:0                 LISTENING       928
  UDP    0.0.0.0:53             *:*                                    3708
  UDP    127.0.0.1:5353         *:*                                    1532
"""
    rows = port_cleaner.parse_netstat(text)
    assert ("TCP", 135, 928) in rows, rows
    assert ("TCP", 8080, 11520) in rows, rows
    # Established connections are not bound ports.
    assert ("TCP", 50000, 11520) not in rows, rows
    # IPv4 and IPv6 rows for the same listener collapse into one.
    assert rows.count(("TCP", 135, 928)) == 1, rows
    assert ("UDP", 53, 3708) in rows, rows
    assert len(rows) == 4, rows


def test_parse_netstat_on_a_localized_windows():
    # German Windows prints its own state word (in the OEM code page), so the
    # parser must recognise a listener by its zero peer port instead.
    text = (
        "  TCP    0.0.0.0:8080        0.0.0.0:0              ABHÖREN         4242\n"
        "  TCP    10.0.0.5:51000      93.184.216.34:443      HERGESTELLT     4242\n"
    )
    rows = port_cleaner.parse_netstat(text)
    assert rows == [("TCP", 8080, 4242)], rows


def test_parse_tasklist():
    text = (
        '"System Idle Process","0","Services","0","8 K"\n'
        '"chrome.exe","1234","Console","1","218,228 K"\n'
        "garbage line\n"
        '"broken","not-a-pid","Console","1","1 K"\n'
    )
    names = port_cleaner.parse_tasklist(text)
    assert names[0] == "System Idle Process", names
    assert names[1234] == "chrome.exe", names
    assert len(names) == 2, names


def test_unknown_process_fails_closed():
    unknown = entry(pid=1052, port=8000, name="PID 1052", known=False)
    assert port_cleaner._is_protected(unknown) is True
    assert "không xác định được tiến trình" in unknown.reasons, unknown.reasons


def test_protection_reasons_do_not_repeat():
    core = entry(pid=4, port=1234, name="System", known=True)
    assert port_cleaner._is_protected(core) is True
    assert core.reasons.count("tiến trình hệ thống") == 1, core.reasons


def test_protection_layers():
    by_name = entry(pid=500, port=1234, name="svchost.exe")
    assert port_cleaner._is_protected(by_name) is True
    # DNS must never be closed: it takes the network down.
    by_port = entry(pid=5000, port=53, protocol="UDP")
    assert port_cleaner._is_protected(by_port) is True
    by_path = entry(
        pid=6000, port=1234, name="weird.exe", exe=r"C:\Windows\System32\weird.exe"
    )
    assert port_cleaner._is_protected(by_path) is True
    app = entry(
        pid=7000,
        port=9222,
        name="chrome.exe",
        exe=r"C:\Program Files\Google\Chrome\chrome.exe",
    )
    assert port_cleaner._is_protected(app) is False


def test_release_ports_kills_each_pid_once():
    calls = []

    def fake_terminate(pid):
        calls.append(pid)
        return pid == 100

    original = port_cleaner.terminate
    port_cleaner.terminate = fake_terminate
    try:
        entries = [
            entry(pid=100, port=80),
            entry(pid=100, port=81),
            entry(pid=200, port=80),
            entry(pid=4, port=135, name="System"),  # protected, untouched
        ]
        port_cleaner._is_protected(entries[-1])
        killed, failed = port_cleaner.release_ports(entries)
    finally:
        port_cleaner.terminate = original

    assert calls == [100, 200], calls
    # Both ports of the surviving pid count as closed ...
    assert [item.port for item in killed] == [80, 81], [item.port for item in killed]
    assert [item.port for item in failed] == [80], [item.port for item in failed]


def test_release_ports_leaves_a_process_holding_a_protected_port():
    """Killing that process would close the protected port too."""
    calls = []
    original = port_cleaner.terminate
    port_cleaner.terminate = lambda pid: calls.append(pid) or True
    try:
        dns = entry(pid=300, port=53, protocol="UDP")
        web = entry(pid=300, port=8080)
        assert port_cleaner._is_protected(dns) is True
        entries = [dns, web]
        killed, failed = port_cleaner.release_ports(entries)
    finally:
        port_cleaner.terminate = original

    assert calls == [], calls
    assert killed == [], killed
    assert [item.port for item in failed] == [8080], [item.port for item in failed]


def test_list_bound_ports_fails_closed_when_the_name_is_unknown():
    """The guard must hold end to end, not only inside _is_protected()."""

    class NetstatResult:
        returncode = 0
        stdout = "  TCP    0.0.0.0:9000        0.0.0.0:0              LISTENING       4242\n"
        stderr = ""

    original_info = port_cleaner._process_info_map
    original_run = port_cleaner._run
    port_cleaner._process_info_map = lambda: ({}, {})
    port_cleaner._run = lambda *args, **kwargs: NetstatResult()
    try:
        entries = port_cleaner.list_bound_ports()
    finally:
        port_cleaner._process_info_map = original_info
        port_cleaner._run = original_run

    assert len(entries) == 1, entries
    assert entries[0].known_name is False
    assert entries[0].protected is True
    assert "không xác định được tiến trình" in entries[0].reasons, entries[0].reasons


def test_terminate_treats_gone_process_as_success():
    class Result:
        returncode = 128  # taskkill: process not found

    original = port_cleaner._run
    port_cleaner._run = lambda *args, **kwargs: Result()
    try:
        assert port_cleaner.terminate(4242) is True
    finally:
        port_cleaner._run = original


if __name__ == "__main__":
    test_parse_netstat()
    test_parse_netstat_on_a_localized_windows()
    test_parse_tasklist()
    test_unknown_process_fails_closed()
    test_protection_reasons_do_not_repeat()
    test_protection_layers()
    test_release_ports_kills_each_pid_once()
    test_release_ports_leaves_a_process_holding_a_protected_port()
    test_list_bound_ports_fails_closed_when_the_name_is_unknown()
    test_terminate_treats_gone_process_as_success()
    print("port_cleaner self-check OK")
