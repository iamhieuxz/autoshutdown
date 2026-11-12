"""Regenerate the docs screenshots from the real widgets.

Run: python make_screenshots.py
"""

import sys

from PyQt5.QtWidgets import QApplication

import AutoShutdown as ui

app = QApplication(sys.argv)
app.setFont(ui.QFont("Segoe UI", 10))


def grab(widget, path):
    widget.show()
    app.processEvents()
    widget.grab().save(path)
    widget.hide()


popup = ui.ModernPopup()
grab(popup, "docs/screenshot-schedule.png")

popup.switch_page(1)
popup.refresh_ports()
grab(popup, "docs/screenshot-ports.png")

popup.switch_page(2)
popup._set_wake_status("Đã hẹn bật máy lúc 06:30 04/11/2026", "on")
grab(popup, "docs/screenshot-wake.png")

panel = ui.CountdownPanel()
panel.start(3725, False)
grab(panel, "docs/screenshot-countdown.png")

peek = ui.PeekIndicator()
peek.set_state(0.42, "1h02")
grab(peek, "docs/screenshot-peek.png")

print("screenshots updated")
