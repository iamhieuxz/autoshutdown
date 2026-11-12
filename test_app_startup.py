"""Self-check that the whole app can be built: tray menu, popup, countdown panel.

This catches startup crashes (e.g. a wrong icon type passed to QMenu.addAction)
that the per-widget self-checks cannot see. Run: python test_app_startup.py
"""

import sys

import AutoShutdown as ui


def test_app_starts():
    try:
        auto = ui.AutoShutdownApp()
    except SystemExit:
        # Another copy of the app owns the single-instance lock.
        print("app startup self-check skipped: Auto Shutdown is already running")
        return

    try:
        menu = auto.tray.contextMenu()
        assert menu is not None, "tray menu missing"
        actions = [action for action in menu.actions() if action.text()]
        assert len(actions) == 5, [action.text() for action in actions]
        # Every menu entry that shows an icon must really carry a QIcon.
        assert all(not action.icon().isNull() for action in actions[:3]), "missing icon"

        # Opening the window from the tray is the main entry point.
        assert auto.popup is None
        actions[0].trigger()
        assert auto.popup is not None, "tray action did not build the popup"
        assert_tabs_fit(auto.popup)

        auto.popup.hide()
        auto.tray.hide()
        auto.countdown_panel.hide_panel()
    finally:
        auto.app.quit()


def assert_tabs_fit(popup):
    """No tab may need more height than the window gives it.

    The wake tab used to need 294px inside a 275px page, so Qt squeezed its time
    card until the digits were clipped - invisible to every other test.
    """
    popup.grab()  # forces the layouts to run before we read their geometry
    available = popup.stack.height()
    assert available > 0, available
    for index in range(popup.stack.count()):
        popup.stack.setCurrentIndex(index)
        page = popup.stack.currentWidget()
        page.layout().activate()
        needed = page.layout().minimumSize().height()
        assert needed <= available, (index, needed, available)



if __name__ == "__main__":
    test_app_starts()
    print("app startup self-check OK")
    sys.exit(0)
