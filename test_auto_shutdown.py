"""Self-check for the shutdown-time preview logic. Run: python test_auto_shutdown.py"""

import json
import os
import sys
import tempfile

from PyQt5.QtCore import QDateTime, QTime
from PyQt5.QtWidgets import QApplication, QMessageBox

import AutoShutdown as ui

app = QApplication(sys.argv)


def test_eta():
    now = QTime(22, 20)
    # A time later today stays today.
    seconds, when = ui.shutdown_eta(now, QTime(23, 30))
    assert seconds == 70 * 60, seconds
    assert when == "hôm nay", when

    # A time already past rolls over to tomorrow.
    seconds, when = ui.shutdown_eta(now, QTime(2, 30))
    assert seconds == 4 * 3600 + 10 * 60, seconds
    assert when == "ngày mai", when

    # The exact current minute counts as tomorrow, matching set_shutdown().
    seconds, when = ui.shutdown_eta(now, QTime(22, 20))
    assert seconds == 86400, seconds
    assert when == "ngày mai", when


def test_settings_write_is_atomic():
    original = ui.SETTINGS_FILE
    directory = tempfile.mkdtemp()
    ui.SETTINGS_FILE = os.path.join(directory, "settings.json")
    try:
        ui.save_settings({"panel_pos": [10, 20]})
        with open(ui.SETTINGS_FILE, "r", encoding="utf-8") as handle:
            assert json.load(handle) == {"panel_pos": [10, 20]}
        # The temp file must be gone: a leftover would overwrite the next save.
        assert not os.path.exists(ui.SETTINGS_FILE + ".tmp")
        # A corrupt file must not crash the loader.
        with open(ui.SETTINGS_FILE, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        assert ui.load_settings() == {}
    finally:
        ui.SETTINGS_FILE = original
        for name in os.listdir(directory):
            os.remove(os.path.join(directory, name))
        os.rmdir(directory)


def test_run_quiet_reports_missing_command():
    # A missing executable must return None instead of raising.
    assert ui._run_quiet(["definitely-not-a-real-command-xyz"]) is None


def test_confirm_port_cleanup():
    asked = {}

    def fake_question(parent, title, text, buttons, default):
        asked["text"] = text
        asked["default"] = default
        asked["buttons"] = buttons
        asked["parent"] = parent
        return QMessageBox.No

    original = QMessageBox.question
    QMessageBox.question = staticmethod(fake_question)
    try:
        entries = [ui.port_cleaner.PortEntry(pid=1, port=80, protocol="TCP")]
        assert ui.confirm_port_cleanup(entries) is False
        assert "1 tiến trình" in asked["text"], asked["text"]
        # Enter must not kill anything: the safe button has to be the default.
        assert asked["default"] == QMessageBox.No, asked["default"]
        assert asked["buttons"] == QMessageBox.Yes | QMessageBox.No, asked["buttons"]

        QMessageBox.question = staticmethod(
            lambda parent, title, text, buttons, default: QMessageBox.Yes
        )
        assert ui.confirm_port_cleanup(entries) is True

        # Two PIDs sharing one image name are two processes, not one.
        twins = [
            ui.port_cleaner.PortEntry(
                pid=pid, port=port, protocol="TCP", process_name="chrome.exe"
            )
            for pid, port in ((10, 100), (11, 200))
        ]
        asked.clear()
        QMessageBox.question = staticmethod(fake_question)
        ui.confirm_port_cleanup(twins)
        assert "2 tiến trình" in asked["text"], asked["text"]

        # More than five processes are summarised, not listed in full.
        many = [
            ui.port_cleaner.PortEntry(
                pid=index, port=1000 + index, protocol="TCP",
                process_name=f"app{index}.exe",
            )
            for index in range(7)
        ]
        asked.clear()
        ui.confirm_port_cleanup(many)
        assert "..." in asked["text"], asked["text"]
        assert "7 tiến trình" in asked["text"], asked["text"]
    finally:
        QMessageBox.question = original


class FakeLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class FakePanel:
    def __init__(self):
        self.shutdown_deadline = QDateTime.currentDateTime()
        self.status_label = FakeLabel()

    def update_countdown(self):
        pass


class FakeTray:
    def __init__(self):
        self.messages = []

    def showMessage(self, *args):
        self.messages.append(args)


class FakeAppForTick:
    clean_ports_on_shutdown = True
    ports_closed = False

    def __init__(self):
        self.countdown_panel = FakePanel()
        self.tray = FakeTray()


def error_titles(app):
    return [message[0] for message in app.tray.messages if "Lỗi" in message[0]]


def test_pre_shutdown_cleanup_does_not_ask_and_tolerates_1190():
    results = []

    def fake_run(command):
        return results.pop(0)

    class Code:
        def __init__(self, returncode):
            self.returncode = returncode

    original_run = ui._run_quiet
    original_list = ui.port_cleaner.list_bound_ports
    original_release = ui.port_cleaner.release_ports
    ui._run_quiet = fake_run
    ui.port_cleaner.list_bound_ports = lambda: []
    ui.port_cleaner.release_ports = lambda entries: ([], [])
    try:
        # 1190 = a shutdown is already scheduled: Windows will still power off.
        app = FakeAppForTick()
        results.append(Code(1190))
        ui.AutoShutdownApp.tick_countdown(app)
        assert "theo lịch ban đầu" in app.countdown_panel.status_label.text
        assert error_titles(app) == [], error_titles(app)

        # Any other failure is reported, with the admin hint.
        app = FakeAppForTick()
        results.append(Code(5))
        ui.AutoShutdownApp.tick_countdown(app)
        assert "quyền admin" in app.countdown_panel.status_label.text
        assert error_titles(app) == ["Lỗi tắt máy"], error_titles(app)

        # A successful immediate shutdown shows no error.
        app = FakeAppForTick()
        results.append(Code(0))
        ui.AutoShutdownApp.tick_countdown(app)
        assert error_titles(app) == [], error_titles(app)
    finally:
        ui._run_quiet = original_run
        ui.port_cleaner.list_bound_ports = original_list
        ui.port_cleaner.release_ports = original_release


def test_format_duration():
    assert ui.format_duration(0) == "0 giây"
    assert ui.format_duration(41) == "41 giây"
    assert ui.format_duration(65) == "1 phút 05 giây"
    assert ui.format_duration(3600) == "1 giờ 00 phút"
    assert ui.format_duration(3900) == "1 giờ 05 phút"
    assert ui.format_duration(-5) == "0 giây"


def test_default_time_is_not_seconds_away():
    """The old default (now + 1 minute) made the balloon read "0 giờ 0 phút"."""
    hour, minute = ui.clock_in(30)
    assert 0 <= hour <= 23 and 0 <= minute <= 59
    seconds, _ = ui.shutdown_eta(QTime.currentTime(), QTime(hour, minute))
    assert seconds >= 25 * 60, seconds


if __name__ == "__main__":
    test_eta()
    test_settings_write_is_atomic()
    test_run_quiet_reports_missing_command()
    test_confirm_port_cleanup()
    test_pre_shutdown_cleanup_does_not_ask_and_tolerates_1190()
    test_format_duration()
    test_default_time_is_not_seconds_away()
    print("shutdown_eta self-check OK")
    sys.exit(0)
