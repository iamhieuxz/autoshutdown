import json
import logging
import os
import sys
import subprocess
import tempfile
from logging.handlers import RotatingFileHandler

from PyQt5.QtCore import (
    QDateTime,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSharedMemory,
    QSize,
    QTime,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPixmap,
    QPen,
    QPolygonF,
)
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QStackedWidget,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtWidgets import QAction

import port_cleaner
import wake_scheduler

SETTINGS_FILE = os.path.join(
    os.path.expanduser("~"), ".autoshutdown_settings.json"
)

LOG_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AutoShutdown"
)
LOG_FILE = os.path.join(LOG_DIR, "autoshutdown.log")

# A windowed build has no console, so every console child would flash a cmd
# window without this flag.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _run_quiet(command):
    """Run a console command quietly. Returns None when it cannot run at all."""
    try:
        return subprocess.run(
            command,
            capture_output=True,
            timeout=30,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def format_duration(seconds):
    """Readable duration: 41 giây / 2 phút 05 giây / 1 giờ 03 phút."""
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours} giờ {minutes:02d} phút"
    if minutes:
        return f"{minutes} phút {secs:02d} giây"
    return f"{secs} giây"


def _log_directories():
    """Candidate log directories, most useful first."""
    candidates = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(os.path.join(local_app_data, "AutoShutdown"))
    candidates.append(os.path.join(tempfile.gettempdir(), "AutoShutdown"))
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), "logs"))
    return candidates


def setup_logging():
    """Keep a log file: a windowed build has nowhere else to report failures."""
    global LOG_FILE
    for directory in _log_directories():
        path = os.path.join(directory, "autoshutdown.log")
        try:
            os.makedirs(directory, exist_ok=True)
            handler = RotatingFileHandler(
                path, maxBytes=512_000, backupCount=2, encoding="utf-8"
            )
        except OSError:
            continue
        LOG_FILE = path
        logging.basicConfig(
            level=logging.INFO,
            handlers=[handler],
            format="%(asctime)s %(levelname)s %(message)s",
        )
        return
    # No file is writable: keep the process working, just without a log file.
    logging.basicConfig(level=logging.INFO)


def install_excepthook():
    """Report crashes instead of dying silently behind the tray icon."""

    def report(exc_type, exc_value, traceback):
        logging.error("Unhandled exception", exc_info=(exc_type, exc_value, traceback))
        app = QApplication.instance()
        if app is not None and hasattr(app, "tray"):
            app.tray.showMessage(
                "Auto Shutdown gặp lỗi",
                f"Xem chi tiết trong {LOG_FILE}",
                QSystemTrayIcon.Critical,
                5000,
            )
        if sys.stderr is not None:
            sys.__excepthook__(exc_type, exc_value, traceback)

    sys.excepthook = report


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        # First run, no settings file yet
        return {}
    except (json.JSONDecodeError, ValueError):
        # Corrupted settings file
        logging.warning(f"Settings file corrupted: {SETTINGS_FILE}")
        return {}
    except OSError as e:
        # Permission or IO error
        logging.warning(f"Cannot read settings: {e}")
        return {}


def save_settings(settings):
    """Write through a temp file so an interrupted save cannot corrupt JSON."""
    temp_path = SETTINGS_FILE + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
        os.replace(temp_path, SETTINGS_FILE)
    except OSError:
        pass


def confirm_port_cleanup(entries, parent=None):
    """Closing a port kills its whole process: ask, and keep the dialog above it."""
    names = sorted({entry.process_name for entry in entries})
    process_count = len({entry.pid for entry in entries})
    preview = ", ".join(names[:5])
    if len(names) > 5:
        preview += ", ..."
    answer = QMessageBox.question(
        parent,
        "Đóng cổng mạng",
        f"Sẽ đóng {process_count} tiến trình đang giữ {len(entries)} cổng:\n{preview}\n\n"
        "Dữ liệu chưa lưu trong các ứng dụng này sẽ mất. Tiếp tục?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return answer == QMessageBox.Yes


# ---------------------------------------------------------------------------
# Design tokens: 4px spacing grid, consistent radii, semantic color palette
# ---------------------------------------------------------------------------
class Token:
    space_1 = 4
    space_2 = 8
    space_3 = 12
    space_4 = 16
    space_6 = 24
    space_8 = 32

    radius_sm = 8
    radius_md = 12
    radius_lg = 16
    radius_xl = 22

    surface = "#111827"
    surface_top = "#141F31"
    surface_input = "#0B1220"
    surface_hover = "#1B2638"
    border = "#263247"
    border_strong = "#3A5470"
    border_accent = "#2E6C8E"

    text_primary = "#F8FAFC"
    text_secondary = "#A3B2C7"
    text_muted = "#8B9DBA"
    text_on_accent = "#062033"

    accent = "#22A9D8"
    accent_hover = "#39BDE8"
    accent_pressed = "#1B8CB3"
    accent_soft = "#173247"
    accent_soft_border = "#245677"
    accent_text = "#61D4FF"

    danger = "#E5484D"
    danger_soft = "#3B1A1E"

    focus = "#7FE0FF"
    success = "#3DD68C"


_STYLESHEET_CACHE = None
_ICON_CACHE = {}
_ICON_CACHE_MAX = 100  # Limit icon cache to prevent memory leaks


def icon_pixmap(name, size=22, color=None):
    """Paint crisp line icons so no emoji glyphs leak into the UI."""
    global _ICON_CACHE
    color = color or Token.accent_text
    key = (name, size, color)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    
    # Prevent cache from growing unbounded
    if len(_ICON_CACHE) >= _ICON_CACHE_MAX:
        # Remove oldest 20% of cache entries (FIFO-like behavior via dict iteration)
        to_remove = max(1, _ICON_CACHE_MAX // 5)
        for _ in range(to_remove):
            _ICON_CACHE.pop(next(iter(_ICON_CACHE)), None)
    
    scale = 3  # supersample, then let the device pixel ratio downscale
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.scale(scale, scale)

    pen = QPen(QColor(color), max(1.4, size * 0.085))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    s = float(size)
    center = QPointF(s / 2, s / 2)

    if name == "clock":
        painter.drawEllipse(QRectF(s * 0.14, s * 0.14, s * 0.72, s * 0.72))
        painter.drawLine(center, QPointF(s / 2, s * 0.3))
        painter.drawLine(center, QPointF(s * 0.68, s * 0.6))
    elif name == "close":
        painter.drawLine(QPointF(s * 0.3, s * 0.3), QPointF(s * 0.7, s * 0.7))
        painter.drawLine(QPointF(s * 0.7, s * 0.3), QPointF(s * 0.3, s * 0.7))
    elif name == "opacity":
        # Half-filled circle reads as "opacity" far better than a gear.
        painter.drawEllipse(QRectF(s * 0.16, s * 0.16, s * 0.68, s * 0.68))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPie(
            QRectF(s * 0.16, s * 0.16, s * 0.68, s * 0.68), 90 * 16, 180 * 16
        )
    elif name == "ban":
        painter.drawEllipse(QRectF(s * 0.16, s * 0.16, s * 0.68, s * 0.68))
        painter.drawLine(QPointF(s * 0.28, s * 0.72), QPointF(s * 0.72, s * 0.28))

    painter.end()
    pixmap.setDevicePixelRatio(scale)
    _ICON_CACHE[key] = pixmap
    return pixmap


def icon_label(name, size=22, color=None, box=44):
    """A rounded tile holding a line icon, matching the header style."""
    label = QLabel()
    label.setFixedSize(box, box)
    label.setAlignment(Qt.AlignCenter)
    label.setPixmap(icon_pixmap(name, size, color))
    return label


_CHECK_ICON_PATH = None


def check_icon_path():
    """Real checkmark glyph so the checkbox state is not conveyed by color alone."""
    global _CHECK_ICON_PATH
    if _CHECK_ICON_PATH is not None:
        return _CHECK_ICON_PATH
    
    # Try to save to temp dir, fallback to memory if it fails
    path = os.path.join(tempfile.gettempdir(), "autoshutdown_check.png")
    pixmap = QPixmap(17, 17)  # 1:1 with the indicator size, Qt does not scale it
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(Token.text_on_accent), 2.2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline(QPolygonF([QPointF(3.5, 8.5), QPointF(7, 12), QPointF(13, 4.5)]))
    painter.end()
    
    try:
        pixmap.save(path)
        _CHECK_ICON_PATH = path.replace(os.sep, "/")
    except (OSError, RuntimeError):
        # If temp dir not writable, use memory path marker
        _CHECK_ICON_PATH = "memory://check"
    
    return _CHECK_ICON_PATH


def build_stylesheet():
    global _STYLESHEET_CACHE
    if _STYLESHEET_CACHE is not None:
        return _STYLESHEET_CACHE
    
    _STYLESHEET_CACHE = f"""
        #container {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 {Token.surface_top},
                stop: 1 {Token.surface}
            );
            border: 1px solid {Token.border};
            border-radius: {Token.radius_xl}px;
        }}
        #headerIcon {{
            background: {Token.accent_soft};
            border: 1px solid {Token.accent_soft_border};
            border-radius: {Token.radius_md}px;
            color: {Token.accent_text};
            font-size: 26px;
            font-weight: 600;
        }}
        #title {{
            color: {Token.text_primary};
            font-size: 22px;
            font-weight: 700;
        }}
        #subtitle {{
            color: {Token.text_secondary};
            font-size: 12px;
        }}
        #closeButton {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: {Token.radius_sm}px;
            color: {Token.text_muted};
            padding: 0;
        }}
        #closeButton:hover {{
            background: {Token.border};
            color: {Token.text_primary};
        }}
        #closeButton:focus {{
            color: {Token.text_primary};
            border: 1px solid {Token.focus};
        }}
        #sectionLabel {{
            color: {Token.text_primary};
            font-size: 13px;
            font-weight: 600;
        }}
        #timeContainer {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #0D1626,
                stop: 1 {Token.surface_input}
            );
            border: 1px solid {Token.border_strong};
            border-radius: {Token.radius_lg}px;
        }}
        #timeCaption {{
            color: {Token.accent_text};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
        }}
        #spinnerDisplay {{
            background: transparent;
            border: none;
            color: {Token.text_primary};
            font-size: 34px;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 0;
        }}
        #noteCard {{
            background: #0D1729;
            border: 1px solid {Token.border};
            border-radius: {Token.radius_md}px;
        }}
        #noteCard QLabel {{
            color: {Token.text_muted};
            font-size: 11px;
        }}
        #statusChip {{
            background: {Token.surface_input};
            border: 1px solid {Token.border};
            border-radius: {Token.radius_sm}px;
            color: {Token.text_secondary};
            font-size: 11px;
            font-weight: 600;
            padding: {Token.space_1}px {Token.space_3}px;
        }}
        #statusChip[state="on"] {{
            background: #10281F;
            border-color: #1F6B4A;
            color: {Token.success};
        }}
        #statusChip[state="warn"] {{
            background: #2B2110;
            border-color: #6B5320;
            color: #F5C86B;
        }}
        #schedulePreview {{
            color: {Token.accent_text};
            font-size: 11px;
            font-weight: 600;
        }}
        #secondaryButton, #primaryButton {{
            border-radius: {Token.radius_md}px;
            font-size: 13px;
            font-weight: 600;
        }}
        #secondaryButton {{
            background: {Token.surface_hover};
            border: 1px solid #34445C;
            color: #CBD5E1;
        }}
        #secondaryButton:hover {{
            background: #26364D;
            border-color: #49617D;
            color: {Token.text_primary};
        }}
        #secondaryButton:pressed {{
            background: #1F2C3E;
        }}
        #secondaryButton:focus {{
            border: 1px solid {Token.focus};
        }}
        #primaryButton {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 {Token.accent_hover},
                stop: 1 {Token.accent}
            );
            border: 1px solid {Token.accent_hover};
            color: {Token.text_on_accent};
        }}
        #primaryButton:hover {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #5AD2F5,
                stop: 1 {Token.accent_hover}
            );
        }}
        #primaryButton:pressed {{
            background: {Token.accent_pressed};
            border-color: {Token.accent_pressed};
        }}
        #primaryButton:focus {{
            border: 1px solid {Token.focus};
        }}
        #primaryButton:disabled {{
            background: #22303F;
            border-color: {Token.border};
            color: {Token.text_muted};
        }}

        #countdownPanel {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 {Token.surface_top},
                stop: 1 #0C1421
            );
            border: 1px solid {Token.border_accent};
            border-radius: {Token.radius_lg}px;
        }}
        #countdownIcon {{
            background: {Token.accent_soft};
            border: 1px solid {Token.accent_soft_border};
            border-radius: {Token.radius_sm}px;
            color: {Token.accent_text};
            font-size: 18px;
            font-weight: 600;
        }}
        #countdownCaption {{
            color: {Token.text_secondary};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
        }}
        #countdownValue {{
            color: {Token.text_primary};
            font-size: 30px;
            font-weight: 700;
        }}
        #countdownTarget {{
            color: {Token.text_muted};
            font-size: 11px;
        }}
        #countdownCancel {{
            background: {Token.danger_soft};
            border: 1px solid #6B2A2E;
            border-radius: {Token.radius_sm}px;
            color: #FF9A9C;
            font-size: 11px;
            font-weight: 600;
            padding: {Token.space_1}px {Token.space_3}px;
        }}
        #countdownCancel:hover {{
            background: #4E2226;
            color: #FFD2D3;
        }}
        #flipSeparator {{
            color: {Token.text_muted};
            font-size: 21px;
            font-weight: 700;
            padding: 0 1px;
        }}
        #countdownProgress {{
            background: #1E2C42;
            border: none;
            border-radius: 2px;
        }}
        #countdownProgress::chunk {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 {Token.accent_pressed},
                stop: 1 {Token.accent_hover}
            );
            border-radius: 2px;
        }}
        #iconButton {{
            background: {Token.surface_input};
            border: 1px solid {Token.border};
            border-radius: {Token.radius_sm}px;
            color: {Token.text_secondary};
            padding: 0;
        }}
        #iconButton:hover {{
            background: {Token.accent_soft};
            border-color: {Token.accent_soft_border};
            color: {Token.accent_text};
        }}
        #opacityLabel {{
            color: {Token.text_secondary};
            font-size: 11px;
            font-weight: 600;
        }}
        #opacityValue {{
            color: {Token.accent_text};
            font-size: 11px;
            font-weight: 700;
        }}
        #opacitySlider {{
            background: transparent;
            height: 20px;
        }}
        #opacitySlider::groove:horizontal {{
            background: {Token.surface_input};
            border: 1px solid {Token.border};
            border-radius: 4px;
            height: 6px;
        }}
        #opacitySlider::sub-page:horizontal {{
            background: {Token.accent};
            border-radius: 4px;
            height: 6px;
        }}
        #opacitySlider::handle:horizontal {{
            background: {Token.accent_hover};
            border: 1px solid {Token.text_primary};
            border-radius: 7px;
            width: 13px;
            margin: -5px 0;
        }}
        #opacityPopup {{
            background: {Token.surface};
            border: 1px solid {Token.border};
            border-radius: {Token.radius_md}px;
        }}

        #segments {{
            background: {Token.surface_input};
            border: 1px solid {Token.border};
            border-radius: {Token.radius_md}px;
        }}
        QPushButton#segButton {{
            background: transparent;
            border: none;
            border-radius: {Token.radius_md}px;
            color: {Token.text_secondary};
            font-size: 12px;
            font-weight: 600;
            padding: {Token.space_2}px {Token.space_3}px;
        }}
        QPushButton#segButton:hover {{
            color: {Token.text_primary};
            background: {Token.surface_hover};
        }}
        QPushButton#segButton:checked {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 {Token.accent_hover},
                stop: 1 {Token.accent}
            );
            color: {Token.text_on_accent};
        }}
        QPushButton#segButton:focus {{
            border: 1px solid {Token.focus};
        }}
        #portSummary {{
            color: {Token.text_secondary};
            font-size: 11px;
        }}
        #portList {{
            background: {Token.surface_input};
            border: 1px solid {Token.border};
            border-radius: {Token.radius_md}px;
            color: {Token.text_primary};
            font-family: "Cascadia Mono", "Consolas", monospace;
            font-size: 11px;
            padding: {Token.space_1}px;
            outline: none;
        }}
        #portList::item {{
            padding: {Token.space_2}px {Token.space_2}px;
            border-radius: {Token.radius_sm}px;
            margin: 1px 0;
        }}
        #portList::item:selected {{
            background: {Token.accent_soft};
            color: {Token.text_primary};
        }}
        #portList::item:hover {{
            background: #16223A;
        }}
        #reloadButton {{
            background: {Token.surface_input};
            border: 1px solid {Token.border_strong};
            border-radius: {Token.radius_sm}px;
            color: {Token.text_secondary};
            font-size: 11px;
            font-weight: 600;
            padding: {Token.space_1}px {Token.space_3}px;
        }}
        #reloadButton:hover {{
            background: {Token.accent_soft};
            color: {Token.text_primary};
        }}
        #reloadButton:focus {{
            border-color: {Token.focus};
        }}
        #cleanPortsButton {{
            background: #B4432F;
            border: 1px solid #E0715C;
            border-radius: {Token.radius_md}px;
            color: #FFFFFF;
            font-size: 13px;
            font-weight: 600;
        }}
        #cleanPortsButton:hover {{
            background: #CC5540;
        }}
        #cleanPortsButton:pressed {{
            background: #9A3826;
        }}
        #cleanPortsButton:focus {{
            border-color: {Token.focus};
        }}
        #cleanPortsButton:disabled {{
            background: #2A3341;
            border-color: {Token.border};
            color: {Token.text_muted};
        }}
        QCheckBox {{
            color: {Token.text_secondary};
            font-size: 12px;
            spacing: {Token.space_2}px;
            padding: {Token.space_1}px 0;
        }}
        QCheckBox:hover {{
            color: {Token.text_primary};
        }}
        QCheckBox::indicator {{
            width: 17px;
            height: 17px;
            border-radius: 5px;
            border: 1px solid {Token.border_strong};
            background: {Token.surface_input};
        }}
        QCheckBox::indicator:hover {{
            border-color: {Token.accent};
        }}
        QCheckBox::indicator:focus {{
            border-color: {Token.focus};
        }}
        QCheckBox::indicator:checked {{
            background: {Token.accent};
            border-color: {Token.accent_hover};
            image: url("{check_icon_path()}");
        }}
    """
    return _STYLESHEET_CACHE


def shutdown_eta(now, target):
    """Seconds until the next occurrence of `target`, plus a "today/tomorrow" label.

    Mirrors the arithmetic in set_shutdown() so the preview text can never
    promise a different time than the command that actually runs.
    """
    seconds = now.secsTo(target)
    if seconds <= 0:
        seconds += 86400
    return seconds, ("hôm nay" if target > now else "ngày mai")


def clock_in(minutes):
    """(hour, minute) of the clock time `minutes` from now."""
    target = QTime.currentTime().addSecs(int(minutes) * 60)
    return target.hour(), target.minute()


class ModernPopup(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 470)
        self._drag_position = None
        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.setInterval(500)
        self._persist_timer.timeout.connect(self._do_persist_position)
        self.setup_ui()
        self.move_to_default_position()
        self._restore_position(load_settings().get("popup_pos"))

    def dismiss(self):
        """Hide the window completely so nothing lingers on screen."""
        self.hide()
        self.close()

    def showEvent(self, event):
        # The popup is reused, so the "today/tomorrow" line must be recomputed.
        if hasattr(self, "schedule_preview"):
            self._refresh_schedule_preview()
        super().showEvent(event)

    def move_to_default_position(self):
        """Default anchor: bottom-right corner of the screen."""
        screen = QApplication.desktop().screenGeometry()
        self.move(
            screen.right() - self.width() - Token.space_4,
            screen.bottom() - self.height() - Token.space_4,
        )

    def _restore_position(self, position):
        if not position or len(position) != 2:
            return
        screen = QApplication.desktop().screenGeometry()
        x = int(position[0])
        y = int(position[1])
        if screen.contains(x + 40, y + 40):
            self.move(x, y)

    def _persist_position(self):
        """Debounced: only save after 500ms without movement."""
        self._persist_timer.start()

    def _do_persist_position(self):
        settings = load_settings()
        settings["popup_pos"] = [self.x(), self.y()]
        save_settings(settings)

    def setup_ui(self):
        container = QFrame(self)
        container.setObjectName("container")
        container.setGeometry(10, 10, 480, 450)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 130))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            Token.space_8, Token.space_6, Token.space_8, Token.space_6
        )
        layout.setSpacing(0)

        # --- Header: 24px vertical rhythm, 12px gap between icon and text ---
        header = QHBoxLayout()
        header.setSpacing(Token.space_3)
        header.setContentsMargins(0, 0, 0, 0)

        icon = icon_label("clock", 24, Token.accent_text, 44)
        icon.setObjectName("headerIcon")
        header.addWidget(icon, 0, Qt.AlignTop)

        title_group = QVBoxLayout()
        title_group.setSpacing(Token.space_1)
        title_group.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Auto Shutdown")
        title.setObjectName("title")
        subtitle = QLabel("Lên lịch tắt máy thật đơn giản")
        subtitle.setObjectName("subtitle")
        title_group.addWidget(title)
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch(1)

        close_button = QPushButton()
        close_button.setObjectName("closeButton")
        close_button.setIcon(QIcon(icon_pixmap("close", 16, Token.text_secondary)))
        close_button.setIconSize(QSize(16, 16))
        close_button.setFixedSize(28, 28)
        close_button.setToolTip("Đóng cửa sổ")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.dismiss)
        header.addWidget(close_button, 0, Qt.AlignTop)
        layout.addLayout(header)

        layout.addSpacing(Token.space_6)

        # --- Segmented control ---
        segment_bar = QFrame()
        segment_bar.setObjectName("segments")
        segments = QHBoxLayout(segment_bar)
        segments.setSpacing(Token.space_1)
        segments.setContentsMargins(
            Token.space_1, Token.space_1, Token.space_1, Token.space_1
        )

        self.schedule_segment = QPushButton("Lịch tắt máy")
        self.schedule_segment.setObjectName("segButton")
        self.schedule_segment.setCheckable(True)
        self.schedule_segment.setChecked(True)
        self.schedule_segment.setCursor(Qt.PointingHandCursor)
        self.schedule_segment.clicked.connect(lambda: self.switch_page(0))

        self.ports_segment = QPushButton("Đóng cổng mạng")
        self.ports_segment.setObjectName("segButton")
        self.ports_segment.setCheckable(True)
        self.ports_segment.setCursor(Qt.PointingHandCursor)
        self.ports_segment.clicked.connect(lambda: self.switch_page(1))

        self.wake_segment = QPushButton("Hẹn bật máy")
        self.wake_segment.setObjectName("segButton")
        self.wake_segment.setCheckable(True)
        self.wake_segment.setCursor(Qt.PointingHandCursor)
        self.wake_segment.clicked.connect(lambda: self.switch_page(2))

        segments.addWidget(self.schedule_segment, 1)
        segments.addWidget(self.ports_segment, 1)
        segments.addWidget(self.wake_segment, 1)
        layout.addWidget(segment_bar)
        layout.addSpacing(Token.space_4)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_schedule_tab())
        self.stack.addWidget(self._build_ports_tab())
        self.stack.addWidget(self._build_wake_tab())
        layout.addWidget(self.stack, 1)

        self.setStyleSheet(build_stylesheet())

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        self.schedule_segment.setChecked(index == 0)
        self.ports_segment.setChecked(index == 1)
        self.wake_segment.setChecked(index == 2)
        if index == 2:
            self.refresh_wake_status()

    def _build_wake_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, Token.space_4, 0, 0)
        # Spacing is explicit so this tab keeps the same vertical rhythm as the
        # other two; a layout-wide spacing plus addSpacing made it taller than
        # the page and Qt squeezed the time card until the digits were clipped.
        layout.setSpacing(0)

        intro = QLabel("Hẹn giờ máy tự bật lại sau khi tắt")
        intro.setObjectName("sectionLabel")
        layout.addWidget(intro)
        layout.addSpacing(Token.space_2)

        wake_container = QFrame()
        wake_container.setObjectName("timeContainer")
        wake_layout = QVBoxLayout(wake_container)
        wake_layout.setContentsMargins(
            Token.space_4, Token.space_3, Token.space_4, Token.space_3
        )
        wake_layout.setSpacing(Token.space_1)

        wake_caption = QLabel("GIỜ BẬT MÁY")
        wake_caption.setObjectName("timeCaption")
        wake_layout.addWidget(wake_caption)

        self.wake_time_edit = TimeSpinner(*clock_in(60))
        wake_layout.addWidget(self.wake_time_edit)
        layout.addWidget(wake_container)
        layout.addSpacing(Token.space_2)

        self.wake_status = QLabel("Chưa hẹn giờ bật máy")
        self.wake_status.setObjectName("statusChip")
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.addWidget(self.wake_status)
        status_row.addStretch(1)
        layout.addLayout(status_row)
        layout.addSpacing(Token.space_3)

        note_card = QFrame()
        note_card.setObjectName("noteCard")
        note_layout = QVBoxLayout(note_card)
        note_layout.setContentsMargins(
            Token.space_3, Token.space_2, Token.space_3, Token.space_2
        )
        note = QLabel(
            "Máy tự bật lại đúng giờ đã chọn, kể cả khi đã tắt hoàn toàn. "
            "Cần bật 'Wake on RTC alarm' trong BIOS/UEFI."
        )
        note.setWordWrap(True)
        note_layout.addWidget(note)
        layout.addWidget(note_card)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.setSpacing(Token.space_3)

        cancel_wake_button = QPushButton("Xóa lịch")
        cancel_wake_button.setObjectName("secondaryButton")
        cancel_wake_button.setMinimumHeight(48)
        cancel_wake_button.setCursor(Qt.PointingHandCursor)
        cancel_wake_button.clicked.connect(self.cancel_wake_schedule)
        buttons.addWidget(cancel_wake_button, 1)

        set_wake_button = QPushButton("Hẹn giờ bật máy")
        set_wake_button.setObjectName("primaryButton")
        set_wake_button.setMinimumHeight(48)
        set_wake_button.setCursor(Qt.PointingHandCursor)
        set_wake_button.clicked.connect(self.schedule_wake_task)
        buttons.addWidget(set_wake_button, 1)
        layout.addLayout(buttons)

        return page

    def _set_wake_status(self, text, state="off"):
        self.wake_status.setText(text)
        self.wake_status.setProperty("state", state)
        # Qt only re-evaluates property selectors after a style unpolish.
        self.wake_status.style().unpolish(self.wake_status)
        self.wake_status.style().polish(self.wake_status)

    def refresh_wake_status(self):
        info = wake_scheduler.wake_info()
        if info is None:
            self._set_wake_status("Chưa hẹn giờ bật máy")
        elif info["armed"]:
            self._set_wake_status(f"Đã hẹn bật máy lúc {info['time']}", "on")
        else:
            # The task exists but lost its WakeToRun flag: saying "đã hẹn" here
            # would promise a wake that never happens.
            self._set_wake_status(
                f"Đã đặt lịch lúc {info['time']} nhưng thiếu WakeToRun", "warn"
            )

    def schedule_wake_task(self):
        selected = self.wake_time_edit.time()
        success, message = wake_scheduler.schedule_wake(
            selected.hour(), selected.minute()
        )
        if success:
            logging.info("Wake task registered for %s", message)
            # A registered task is not enough: without the WakeToRun flag the
            # machine never powers itself back on.
            info = wake_scheduler.wake_info()
            armed = bool(info and info["armed"])
            if armed:
                self._set_wake_status(f"Đã hẹn bật máy lúc {message}", "on")
                # The task is armed; whether the RTC actually fires depends on
                # the BIOS, which Windows cannot report.
                notice = (
                    f"Máy sẽ tự bật lại lúc {message}.\n"
                    "Nếu máy vẫn không bật, hãy kiểm tra 'Wake on RTC alarm' trong BIOS/UEFI."
                )
            else:
                self._set_wake_status(
                    f"Đã đặt lịch lúc {message}, nhưng task thiếu cờ WakeToRun.",
                    "warn",
                )
                notice = (
                    "Lịch đã được tạo nhưng task không bật cờ WakeToRun nên máy "
                    "sẽ không tự bật.\nHãy xóa lịch rồi đặt lại, hoặc kiểm tra "
                    "Task Scheduler → AutoShutdown Auto Wake."
                )
            app = QApplication.instance()
            if hasattr(app, "tray"):
                app.tray.showMessage(
                    "Hẹn giờ bật máy",
                    notice,
                    QSystemTrayIcon.Information if armed else QSystemTrayIcon.Warning,
                    4000,
                )
        else:
            logging.warning("Wake task registration failed: %s", message)
            self._set_wake_status(f"Không hẹn được: {message}", "warn")

    def cancel_wake_schedule(self):
        if wake_scheduler.cancel_wake():
            logging.info("Wake task cancelled")
            self._set_wake_status("Đã xóa lịch bật máy")
        else:
            self._set_wake_status("Không có lịch bật máy để xóa")

    def _build_schedule_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, Token.space_4, 0, 0)
        layout.setSpacing(0)

        # --- Section label ---
        intro = QLabel("Chọn thời điểm máy sẽ tự động tắt")
        intro.setObjectName("sectionLabel")
        layout.addWidget(intro)
        layout.addSpacing(Token.space_2)

        # --- Time input card ---
        time_container = QFrame()
        time_container.setObjectName("timeContainer")
        time_layout = QVBoxLayout(time_container)
        time_layout.setContentsMargins(
            Token.space_4, Token.space_3, Token.space_4, Token.space_3
        )
        time_layout.setSpacing(Token.space_1)

        time_caption = QLabel("THỜI GIAN TẮT MÁY")
        time_caption.setObjectName("timeCaption")
        time_layout.addWidget(time_caption)

        self.time_edit = TimeSpinner(*clock_in(30))
        self.time_edit.changed.connect(self._refresh_schedule_preview)
        time_layout.addWidget(self.time_edit)
        layout.addWidget(time_container)

        layout.addSpacing(Token.space_2)

        # Preview answers the real question: today or tomorrow, and how long.
        self.schedule_preview = QLabel()
        self.schedule_preview.setObjectName("schedulePreview")
        layout.addWidget(self.schedule_preview)

        layout.addSpacing(Token.space_3)

        # --- Option: close open ports before shutting down ---
        self.close_ports_checkbox = QCheckBox(
            "Đóng tất cả cổng ứng dụng đang mở trước khi tắt máy"
        )
        self.close_ports_checkbox.setObjectName("optionCheck")
        self.close_ports_checkbox.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.close_ports_checkbox)

        layout.addSpacing(Token.space_6)
        layout.addStretch(1)

        # --- Actions: equal width, equal height ---
        buttons = QHBoxLayout()
        buttons.setSpacing(Token.space_3)

        cancel_button = QPushButton("Hủy")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.setMinimumHeight(48)
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.clicked.connect(self.dismiss)

        set_button = QPushButton("Đặt lịch tắt máy")
        set_button.setObjectName("primaryButton")
        set_button.setMinimumHeight(48)
        set_button.setCursor(Qt.PointingHandCursor)
        set_button.clicked.connect(self.set_shutdown)

        buttons.addWidget(cancel_button, 1)
        buttons.addWidget(set_button, 1)
        layout.addLayout(buttons)

        self._refresh_schedule_preview()
        return page

    def _refresh_schedule_preview(self):
        """Show the real consequence of the chosen time: today, tomorrow, how long."""
        if not hasattr(self, 'time_edit') or self.time_edit is None:
            return
        seconds, when = shutdown_eta(QTime.currentTime(), self.time_edit.time())
        self.schedule_preview.setText(
            f"Máy sẽ tắt {when} lúc {self.time_edit.time().toString('HH:mm')}"
            f" · còn {format_duration(seconds)}"
        )

    def _build_ports_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, Token.space_4, 0, 0)
        layout.setSpacing(Token.space_3)

        header_row = QHBoxLayout()
        header_row.setSpacing(Token.space_2)

        self.port_summary = QLabel("Đang quét các cổng đang mở...")
        self.port_summary.setObjectName("portSummary")
        header_row.addWidget(self.port_summary)
        header_row.addStretch(1)

        reload_button = QPushButton("Làm mới")
        reload_button.setObjectName("reloadButton")
        reload_button.setCursor(Qt.PointingHandCursor)
        reload_button.clicked.connect(self.refresh_ports)
        header_row.addWidget(reload_button)
        layout.addLayout(header_row)

        self.port_list = QListWidget()
        self.port_list.setObjectName("portList")
        self.port_list.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self.port_list, 1)

        note_card = QFrame()
        note_card.setObjectName("noteCard")
        note_layout = QVBoxLayout(note_card)
        note_layout.setContentsMargins(
            Token.space_3, Token.space_2, Token.space_3, Token.space_2
        )
        note = QLabel(
            "Chỉ các tiến trình ứng dụng thường mới có thể đóng. "
            "Tiến trình hệ thống luôn được giữ nguyên."
        )
        note.setWordWrap(True)
        note_layout.addWidget(note)
        layout.addWidget(note_card)

        self.clean_button = QPushButton("Đóng tất cả cổng ứng dụng")
        self.clean_button.setObjectName("cleanPortsButton")
        self.clean_button.setMinimumHeight(48)
        self.clean_button.setCursor(Qt.PointingHandCursor)
        self.clean_button.setEnabled(False)
        self.clean_button.clicked.connect(self.clean_ports)
        layout.addWidget(self.clean_button)

        # Delay initial load so the UI appears responsive.
        QTimer.singleShot(150, self.refresh_ports)
        return page

    def refresh_ports(self):
        entries = port_cleaner.list_bound_ports()
        self.port_list.clear()

        killable = [entry for entry in entries if not entry.protected]
        protected = [entry for entry in entries if entry.protected]

        if not entries:
            item = QListWidgetItem("Không có cổng nào đang mở.")
            item.setForeground(QColor(Token.text_muted))
            item.setFlags(Qt.NoItemFlags)
            self.port_list.addItem(item)
            self.port_summary.setText("0 cổng có thể đóng  •  0 cổng hệ thống")
            self.clean_button.setEnabled(False)
            return

        if killable:
            self._add_port_group(f"ỨNG DỤNG · {len(killable)}", killable, Token.text_primary)
        if protected:
            self._add_port_group(
                f"HỆ THỐNG · BẢO VỆ · {len(protected)}", protected, Token.text_muted
            )

        self.port_summary.setText(
            f"{len(killable)} cổng có thể đóng  •  "
            f"{len(protected)} cổng hệ thống được bảo vệ"
        )
        self.clean_button.setEnabled(bool(killable))

    def _add_port_group(self, title, entries, color):
        header = QListWidgetItem(title)
        header.setForeground(QColor(Token.text_muted))
        header.setFlags(Qt.NoItemFlags)
        font = header.font()
        font.setPointSizeF(max(7.0, font.pointSizeF() - 1.5))
        font.setBold(True)
        header.setFont(font)
        self.port_list.addItem(header)

        for entry in entries:
            # Sanitize process name to remove control chars and newlines
            clean_name = entry.process_name.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # Remove other control characters
            clean_name = ''.join(c if ord(c) >= 32 or c in '\n\r\t' else '?' for c in clean_name)
            clean_name = clean_name.strip()
            
            suffix = f"  [{', '.join(entry.reasons)}]" if entry.protected else ""
            item = QListWidgetItem(
                f"{entry.protocol:<4} :{entry.port:<6} {clean_name}{suffix}"
            )
            item.setForeground(QColor(color))
            if entry.protected:
                item.setFlags(Qt.NoItemFlags)
            self.port_list.addItem(item)

    def clean_ports(self):
        entries = port_cleaner.list_bound_ports()
        killable = [entry for entry in entries if not entry.protected]
        if not killable:
            self.port_summary.setText("Không có cổng ứng dụng nào để đóng.")
            return
        if not confirm_port_cleanup(killable, self):
            return

        killed, failed = port_cleaner.release_ports(killable)
        logging.info("Port cleanup: %s closed, %s failed", len(killed), len(failed))
        self.refresh_ports()

        app = QApplication.instance()
        if hasattr(app, "tray"):
            message = f"Đã đóng {len(killed)} cổng."
            if failed:
                message += f"  {len(failed)} cổng không đóng được."
            app.tray.showMessage(
                "Đóng cổng mạng", message, QSystemTrayIcon.Information, 3000
            )

        self.port_summary.setText(
            f"Đã đóng {len(killed)} cổng"
            + (f"  •  {len(failed)} cổng không đóng được" if failed else "")
        )

    def center_on_screen(self):
        screen = QApplication.desktop().screenGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2,
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_position and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        self._persist_position()
        event.accept()

    def set_shutdown(self):
        if not hasattr(self, 'time_edit') or self.time_edit is None:
            logging.error("time_edit not initialized, cannot schedule shutdown")
            QMessageBox.warning(
                self,
                "Lỗi",
                "Giao diện không sẵn sàng. Hãy thử đóng và mở lại cửa sổ.",
            )
            return
        seconds, _ = shutdown_eta(QTime.currentTime(), self.time_edit.time())

        # Ports are closed at shutdown time, not now.
        clean_ports_on_shutdown = self.close_ports_checkbox.isChecked()

        # Give the app a buffer so it can close the ports right before power off.
        # If the app dies unexpectedly, Windows still shuts the machine down.
        buffer_seconds = 25 if clean_ports_on_shutdown else 0

        result = _run_quiet(
            ["shutdown", "/s", "/t", str(seconds + buffer_seconds)]
        )
        app = QApplication.instance()
        succeeded = result is not None and result.returncode == 0

        if succeeded:
            logging.info(
                "Shutdown scheduled in %ss (buffer %ss, close ports: %s)",
                seconds,
                buffer_seconds,
                clean_ports_on_shutdown,
            )
            if hasattr(app, "tray"):
                message = f"Máy sẽ tắt sau {format_duration(seconds)}."
                if clean_ports_on_shutdown:
                    message += " Cổng mạng sẽ được đóng ngay trước khi tắt."
                app.tray.showMessage(
                    "Đã đặt lịch tắt máy",
                    message,
                    QSystemTrayIcon.Information,
                    3000,
                )
            if hasattr(app, "start_countdown"):
                app.start_countdown(seconds, clean_ports_on_shutdown)
        else:
            code = result.returncode if result is not None else None
            logging.warning("shutdown command failed: %s", code)
            if hasattr(app, "tray"):
                app.tray.showMessage(
                    "Không thể đặt lịch",
                    "Windows không chấp nhận lệnh tắt máy.",
                    QSystemTrayIcon.Critical,
                    3000,
                )
            # Keep the window open: a balloon disappears and leaves the user
            # wondering whether anything was scheduled.
            QMessageBox.warning(
                self,
                "Không thể đặt lịch tắt máy",
                f"Windows từ chối lệnh tắt máy (mã {code}).\n\n"
                "Nếu lỗi lặp lại, hãy chạy Auto Shutdown bằng quyền quản trị "
                "(chuột phải → Run as administrator).",
            )
            return
        self.hide()
        self.close()


class ArrowButton(QToolButton):
    """A small square button that paints a crisp chevron arrow."""

    def __init__(self, direction, parent=None):
        super().__init__(parent)
        self.direction = direction  # 1 = up, -1 = down
        self.setFixedSize(22, 22)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(1, 1, -1, -1)
        if self.underMouse():
            painter.setBrush(QColor(Token.accent))
            painter.setPen(QPen(QColor(Token.accent_hover), 1))
        else:
            painter.setBrush(QColor(Token.accent_soft))
            painter.setPen(QPen(QColor(Token.border_strong), 1))
        painter.drawRoundedRect(rect, 6, 6)

        size = 5.0
        cx = rect.center().x() + 0.5
        cy = rect.center().y() + 0.5

        if self.direction > 0:
            points = [
                QPointF(cx - size, cy + size * 0.6),
                QPointF(cx, cy - size * 0.7),
                QPointF(cx + size, cy + size * 0.6),
            ]
        else:
            points = [
                QPointF(cx - size, cy - size * 0.6),
                QPointF(cx, cy + size * 0.7),
                QPointF(cx + size, cy - size * 0.6),
            ]

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF" if self.underMouse() else "#9CC3DC"))
        painter.drawPolygon(QPolygonF(points))


class TimeSpinner(QWidget):
    """Hour/minute picker with wrapping up/down chevrons."""

    changed = pyqtSignal()

    def __init__(self, hour=None, minute=None, parent=None):
        super().__init__(parent)
        # Validate and normalize input
        if hour is not None:
            if not (0 <= hour <= 23):
                logging.warning(f"Invalid hour {hour}, clamping to valid range")
                hour = max(0, min(23, hour))
            self.hour = hour
        else:
            self.hour = QTime.currentTime().hour()
        
        if minute is not None:
            if not (0 <= minute <= 59):
                logging.warning(f"Invalid minute {minute}, clamping to valid range")
                minute = max(0, min(59, minute))
            self.minute = minute
        else:
            self.minute = (QTime.currentTime().minute() + 1) % 60
        
        self.active_field = 0  # 0 = hour, 1 = minute

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Token.space_2)

        self.display = QLabel()
        self.display.setObjectName("spinnerDisplay")
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setMinimumHeight(56)
        self.display.setCursor(Qt.PointingHandCursor)
        self.display.mousePressEvent = self._on_display_click
        layout.addWidget(self.display, 1)

        buttons = QVBoxLayout()
        buttons.setSpacing(Token.space_1)
        buttons.setContentsMargins(0, 0, 0, 0)

        self.up_button = ArrowButton(1)
        self.up_button.clicked.connect(lambda: self.step(1))
        buttons.addWidget(self.up_button)

        self.down_button = ArrowButton(-1)
        self.down_button.clicked.connect(lambda: self.step(-1))
        buttons.addWidget(self.down_button)
        layout.addLayout(buttons)

        # Keyboard parity with the arrows: Tab reaches the spinner, then
        # Up/Down change the value and Left/Right pick the field.
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip("↑/↓ để chỉnh giờ, ←/→ để chọn giờ hoặc phút")
        self.refresh()

    # -- interaction --------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Up, Qt.Key_Down):
            self.step(1 if key == Qt.Key_Up else -1)
        elif key in (Qt.Key_Left, Qt.Key_Right):
            self.active_field = 0 if key == Qt.Key_Left else 1
            self.refresh()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        if not self.hasFocus():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor(Token.focus), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(
            self.rect().adjusted(0, 0, -1, -1), Token.radius_sm, Token.radius_sm
        )

    def _on_display_click(self, event):
        self.setFocus()
        position = self.display.mapFrom(self, event.pos())
        width = self.display.width()
        self.active_field = 0 if position.x() < width * 0.45 else 1
        self.refresh()

    def step(self, delta):
        if self.active_field == 0:
            self.hour = (self.hour + delta) % 24
        else:
            self.minute = (self.minute + delta) % 60
        self.refresh()
        self.changed.emit()

    def set_time(self, hour, minute):
        self.hour = hour % 24
        self.minute = minute % 60
        self.refresh()
        self.changed.emit()

    def time(self):
        return QTime(self.hour, self.minute)

    def refresh(self):
        # Active field gets the accent color so a click tells you what will change.
        active, idle = Token.accent_text, Token.text_muted
        hour_color = active if self.active_field == 0 else idle
        minute_color = active if self.active_field == 1 else idle
        self.display.setText(
            f"<span style='color:{hour_color}'>{self.hour:02d}</span>"
            f"<span style='color:{Token.text_muted}'>:</span>"
            f"<span style='color:{minute_color}'>{self.minute:02d}</span>"
        )
        self.display.setTextFormat(Qt.RichText)


class FlipDigit(QWidget):
    """A single flip-clock card rendering one digit with a hinged flap."""

    def __init__(self, width=46, height=66, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._value = 0
        self._next_value = 0
        self._flip = 0.0
        self._anim = None

    def _get_flip(self):
        return self._flip

    def _set_flip(self, value):
        self._flip = value
        self.update()

    flip = pyqtProperty(float, fget=_get_flip, fset=_set_flip)

    def set_digit(self, value, animate=True):
        value = int(value) % 10
        if value == self._value and self._anim is None:
            return
        if not animate or self._anim is not None:
            self._value = value
            self._next_value = value
            self._flip = 0.0
            self.update()
            return

        self._next_value = value
        self._anim = QPropertyAnimation(self, b"flip", self)
        self._anim.setDuration(320)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_flip_done)
        self._anim.start()

    def _on_flip_done(self):
        self._value = self._next_value
        self._flip = 0.0
        self._anim = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        width = float(self.width())
        height = float(self.height())
        hinge = height / 2.0

        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0.0, QColor("#1E293B"))
        gradient.setColorAt(0.49, QColor("#182234"))
        gradient.setColorAt(0.51, QColor("#111A29"))
        gradient.setColorAt(1.0, QColor("#0A1120"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(0, 0, width, height), 9, 9)

        font = QFont("Segoe UI", 0)
        font.setBold(True)
        font.setPixelSize(int(height * 0.70))
        painter.setFont(font)
        painter.setPen(QColor(Token.text_primary))

        flipping = self._anim is not None

        bottom_value = self._next_value if flipping else self._value
        painter.save()
        painter.setClipRect(QRectF(0, hinge, width, height - hinge))
        painter.drawText(QRectF(0, 0, width, height), Qt.AlignCenter, str(bottom_value))
        painter.restore()

        painter.save()
        painter.setClipRect(QRectF(0, 0, width, hinge))
        painter.drawText(
            QRectF(0, 0, width, height),
            Qt.AlignCenter,
            str(self._next_value if flipping else self._value),
        )
        painter.restore()

        if flipping:
            painter.save()
            painter.setClipRect(QRectF(0, 0, width, hinge))
            painter.translate(0, hinge)
            painter.scale(1.0, max(0.03, 1.0 - self._flip))
            painter.translate(0, -hinge)
            painter.setOpacity(1.0 - self._flip * 0.30)
            painter.drawText(QRectF(0, 0, width, height), Qt.AlignCenter, str(self._value))
            painter.restore()

        painter.setPen(QColor(0, 0, 0, 150))
        painter.drawLine(QPointF(2, hinge), QPointF(width - 2, hinge))
        painter.setPen(QColor(255, 255, 255, 20))
        painter.drawLine(QPointF(2, hinge + 1), QPointF(width - 2, hinge + 1))


class FlipClock(QWidget):
    """Six digit flip clock: HH MM SS."""

    def __init__(self, digit_width=38, digit_height=54, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.digits = []
        for index in range(6):
            digit = FlipDigit(digit_width, digit_height)
            layout.addWidget(digit)
            self.digits.append(digit)
            if index in (1, 3):
                separator = QLabel(":")
                separator.setObjectName("flipSeparator")
                separator.setAlignment(Qt.AlignCenter)
                layout.addWidget(separator)

    def set_time(self, hours, minutes, seconds, animate=True):
        values = [
            hours // 10, hours % 10,
            minutes // 10, minutes % 10,
            seconds // 10, seconds % 10,
        ]
        for digit, value in zip(self.digits, values):
            digit.set_digit(value, animate)


class OpacityPopup(QWidget):
    """Compact frameless slider used to tune the opacity of a window."""

    def __init__(self, target, initial=100, on_change=None, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.target = target
        self.on_change = on_change
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(150)
        self.setObjectName("opacityPopup")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            Token.space_3, Token.space_2, Token.space_3, Token.space_2
        )
        layout.setSpacing(Token.space_2)

        title = QLabel("Trong suốt")
        title.setObjectName("opacityLabel")
        layout.addWidget(title)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(30, 100)
        self.slider.setValue(initial)
        self.slider.setObjectName("opacitySlider")
        self.slider.setFixedWidth(56)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider)

        self.value_label = QLabel(f"{initial}%")
        self.value_label.setObjectName("opacityValue")
        self.value_label.setFixedWidth(30)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.value_label)

        self.setStyleSheet(build_stylesheet())

    def _on_value_changed(self, value):
        self.target.setWindowOpacity(value / 100.0)
        self.value_label.setText(f"{value}%")
        if self.on_change:
            self.on_change(value)


class PeekIndicator(QWidget):
    """A circular progress ring that peeks out from the screen edge.

    Only a fraction of the circle stays visible so the card does not clutter
    the desktop. Hovering it brings the full countdown panel back.
    """

    DIAMETER = 84
    VISIBLE_RATIO = 3  # only 1/3 of the circle is shown

    def __init__(self, on_expand=None, parent=None):
        super().__init__(
            parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.DIAMETER, self.DIAMETER)
        self.setCursor(Qt.PointingHandCursor)
        self.on_expand = on_expand
        self.progress = 0.0
        self.remaining_text = ""

    def set_state(self, progress, remaining_text):
        self.progress = max(0.0, min(1.0, progress))
        self.remaining_text = remaining_text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        size = self.DIAMETER
        inset = 5
        box = QRectF(inset, inset, size - inset * 2, size - inset * 2)

        painter.setBrush(QColor(11, 18, 32, 235))
        painter.setPen(QPen(QColor(Token.border), 1))
        painter.drawEllipse(box)

        track = QPen(QColor(Token.border), 7)
        track.setCapStyle(Qt.RoundCap)
        painter.setPen(track)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(box, 0, 360 * 16)

        if self.progress > 0:
            arc = QPen(QColor(Token.accent), 7)
            arc.setCapStyle(Qt.RoundCap)
            painter.setPen(arc)
            painter.drawArc(box, 90 * 16, -int(self.progress * 360 * 16))

        font = QFont("Segoe UI", 0)
        font.setBold(True)
        font.setPixelSize(17)
        painter.setFont(font)
        painter.setPen(QColor(Token.text_primary))
        painter.drawText(box, Qt.AlignCenter, self.remaining_text)

    def enterEvent(self, event):
        if self.on_expand:
            self.on_expand()
        event.accept()

    def place_at_edge(self, side, anchor):
        """Tuck the ring against a screen edge so only 1/3 of it stays visible."""
        screen = QApplication.desktop().screenGeometry()
        visible = self.DIAMETER / self.VISIBLE_RATIO
        hidden = self.DIAMETER - visible

        if side == "right":
            # Only the right third of the circle remains on screen.
            x = screen.right() - visible + 1
        else:
            x = screen.left() - hidden + 1

        # Keep the ring at the same height as the panel so it never jumps.
        if anchor is not None:
            y = anchor.y() - self.DIAMETER // 2
        else:
            y = screen.bottom() - self.DIAMETER + 1

        y = max(screen.top() - hidden, min(y, screen.bottom() - visible + 1))
        self.move(int(x), int(y))


class CountdownPanel(QWidget):
    """Draggable always-on-top flip-clock countdown card.

    After a period without mouse interaction the card shrinks into a small
    progress ring tucked against the screen edge. Hovering the ring restores
    the full card.
    """

    IDLE_MS = 30000

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(292, 196)
        self.deadline = None
        self.shutdown_deadline = None
        self.total_seconds = 0
        self.clean_ports_on_shutdown = False
        self._drag_position = None
        self._opacity_popup = None
        self._peek = None
        self._peek_side = "right"
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(self.IDLE_MS)
        self._idle_timer.timeout.connect(self.collapse_to_edge)
        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.setInterval(500)
        self._persist_timer.timeout.connect(self._do_persist_position)
        self.setup_ui()
        self.move_to_corner()
        self._idle_timer.start()

    def setup_ui(self):
        container = QFrame(self)
        container.setObjectName("countdownPanel")
        container.setGeometry(8, 8, 276, 180)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 125))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            Token.space_4, Token.space_3, Token.space_4, Token.space_3
        )
        layout.setSpacing(Token.space_3)

        top_row = QHBoxLayout()
        top_row.setSpacing(Token.space_2)

        caption_group = QVBoxLayout()
        caption_group.setSpacing(0)
        caption = QLabel("MÁY SẼ TẮT LÚC")
        caption.setObjectName("countdownCaption")
        self.target_label = QLabel("—")
        self.target_label.setObjectName("countdownTarget")
        caption_group.addWidget(caption)
        caption_group.addWidget(self.target_label)
        top_row.addLayout(caption_group)
        top_row.addStretch(1)

        self.gear_button = QPushButton()
        self.gear_button.setObjectName("iconButton")
        self.gear_button.setIcon(QIcon(icon_pixmap("opacity", 16, Token.text_secondary)))
        self.gear_button.setIconSize(QSize(16, 16))
        self.gear_button.setFixedSize(28, 28)
        self.gear_button.setToolTip("Điều chỉnh độ trong suốt")
        self.gear_button.setCursor(Qt.PointingHandCursor)
        self.gear_button.clicked.connect(self.toggle_opacity_popup)
        top_row.addWidget(self.gear_button, 0, Qt.AlignTop)

        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.setObjectName("countdownCancel")
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.clicked.connect(self.request_cancel)
        top_row.addWidget(self.cancel_button, 0, Qt.AlignTop)
        layout.addLayout(top_row)

        self.clock = FlipClock()
        clock_row = QHBoxLayout()
        clock_row.setContentsMargins(0, 0, 0, 0)
        clock_row.addStretch(1)
        clock_row.addWidget(self.clock)
        clock_row.addStretch(1)
        layout.addLayout(clock_row)

        self.status_label = QLabel("Đang đếm ngược")
        self.status_label.setObjectName("countdownTarget")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # A thin progress line answers "how far along am I" without reading digits.
        self.progress = QProgressBar()
        self.progress.setObjectName("countdownProgress")
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        layout.addWidget(self.progress)

        self.setStyleSheet(build_stylesheet())

    # -- collapse / expand --------------------------------------------------
    def _ensure_peek(self):
        if self._peek is None:
            self._peek = PeekIndicator(on_expand=self.expand_from_edge)
        return self._peek

    def _nearest_side(self):
        """Pick the screen edge closest to the panel anchor."""
        screen = QApplication.desktop().screenGeometry()
        center_x = self.x() + self.width() // 2

        if abs(screen.right() - center_x) <= abs(center_x - screen.left()):
            return "right"
        return "left"

    def collapse_to_edge(self):
        """Shrink the panel into a ring tucked against the nearest screen edge."""
        if self._peek is None:
            self._ensure_peek()
        if self._peek.isVisible():
            return

        self._peek_side = self._nearest_side()
        anchor = QPointF(self.x() + self.width() / 2, self.y() + self.height() / 2)
        self._peek.set_state(self._current_progress(), self._current_short_text())
        self._peek.place_at_edge(self._peek_side, anchor)
        self._peek.show()
        self._peek.raise_()

        self.hide()
        self._idle_timer.stop()

    def expand_from_edge(self):
        """Restore the full panel when the ring is hovered."""
        if self._peek:
            self._peek.hide()
        self.show()
        self.raise_()
        self.activateWindow()
        self._idle_timer.start()

    def _current_progress(self):
        if not self.deadline or not self.total_seconds:
            return 0.0
        remaining = QDateTime.currentDateTime().secsTo(self.deadline)
        if remaining < 0:
            remaining = 0
        elapsed = self.total_seconds - remaining
        return max(0.0, min(1.0, elapsed / self.total_seconds))

    def _current_short_text(self):
        if not self.deadline:
            return "--:--"
        remaining = QDateTime.currentDateTime().secsTo(self.deadline)
        if remaining <= 0:
            return "00:00"
        minutes = remaining // 60
        secs = remaining % 60
        if minutes >= 60:
            return f"{minutes // 60}h{minutes % 60:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _refresh_peek(self):
        if self._peek and self._peek.isVisible():
            self._peek.set_state(self._current_progress(), self._current_short_text())

    # -- mouse tracking -----------------------------------------------------
    def enterEvent(self, event):
        self._idle_timer.start()
        event.accept()

    def leaveEvent(self, event):
        self._idle_timer.start()
        event.accept()

    # -- opacity ------------------------------------------------------------
    def apply_opacity(self, value):
        self.setWindowOpacity(max(0.3, min(1.0, value / 100.0)))

    def toggle_opacity_popup(self):
        if self._opacity_popup and self._opacity_popup.isVisible():
            self._opacity_popup.close()
            return

        current = int(round(self.windowOpacity() * 100))
        self._opacity_popup = OpacityPopup(
            self,
            initial=current,
            on_change=self._persist_opacity,
        )
        # Anchor the strip to the top-right corner of the panel, outside its body.
        origin = self.gear_button.mapToGlobal(self.gear_button.rect().topLeft())
        popup = self._opacity_popup
        popup.adjustSize()
        x = origin.x() + self.gear_button.width() - popup.width()
        y = origin.y() - popup.height() - Token.space_2
        screen = QApplication.desktop().screenGeometry()
        x = max(screen.left(), min(x, screen.right() - popup.width()))
        y = max(screen.top(), min(y, screen.bottom() - popup.height()))
        popup.move(x, y)
        popup.show()

    def _persist_opacity(self, value):
        settings = load_settings()
        settings["panel_opacity"] = int(value)
        save_settings(settings)

    # -- positioning --------------------------------------------------------
    def move_to_corner(self):
        settings = load_settings()
        position = settings.get("panel_pos")
        screen = QApplication.desktop().screenGeometry()
        if position and len(position) == 2:
            x, y = int(position[0]), int(position[1])
            # A saved position can point off-screen after a monitor change; the
            # countdown would then run invisibly. Validate that the entire window
            # fits within the screen bounds.
            if (screen.left() <= x and 
                x + self.width() <= screen.right() and
                screen.top() <= y and 
                y + self.height() <= screen.bottom()):
                self.move(x, y)
                return
        self.move(
            screen.right() - self.width() - Token.space_4,
            screen.bottom() - self.height() - Token.space_4,
        )

    def _persist_position(self):
        """Debounced: only save after 500ms without movement."""
        self._persist_timer.start()

    def _do_persist_position(self):
        settings = load_settings()
        settings["panel_pos"] = [self.x(), self.y()]
        save_settings(settings)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        # Any pointer movement counts as interaction and keeps the card open.
        self._idle_timer.start()
        if self._drag_position and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        self._persist_position()
        event.accept()

    # -- countdown ----------------------------------------------------------
    def start(self, seconds, clean_ports_on_shutdown=False):
        self.total_seconds = seconds
        self.clean_ports_on_shutdown = clean_ports_on_shutdown
        # deadline: the moment the user asked the machine to power off.
        # shutdown_deadline: when Windows actually cuts the power (includes buffer).
        self.deadline = QDateTime.currentDateTime().addSecs(seconds)
        self.shutdown_deadline = QDateTime.currentDateTime().addSecs(
            seconds + (25 if clean_ports_on_shutdown else 0)
        )
        self.target_label.setText(self.deadline.toString("dd/MM/yyyy HH:mm"))
        self.status_label.setText(
            "Sẽ đóng cổng mạng trước khi tắt"
            if clean_ports_on_shutdown
            else "Đang đếm ngược"
        )
        self.update_countdown()
        self.show()
        self.raise_()
        self.activateWindow()
        self._idle_timer.start()

    def update_countdown(self):
        if self.deadline is None:
            return
        remaining = QDateTime.currentDateTime().secsTo(self.deadline)
        self.progress.setValue(int(self._current_progress() * 1000))
        if remaining <= 0:
            self.clock.set_time(0, 0, 0, animate=False)
            self._refresh_peek()
            return
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        secs = remaining % 60
        self.clock.set_time(hours, minutes, secs)
        self._refresh_peek()

    def request_cancel(self):
        app = QApplication.instance()
        if hasattr(app, "cancel_countdown"):
            app.cancel_countdown()

    def hide_panel(self):
        self._idle_timer.stop()
        if self._peek:
            self._peek.hide()
        self.hide()


class AutoShutdownApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setFont(QFont("Segoe UI", 10))
        # A second copy would fight over the same pending shutdown and tray icon.
        self.instance_lock = QSharedMemory("autoshutdown-single-instance")
        if not self.instance_lock.create(1):
            if "--woke" in sys.argv:
                # The wake task fired while a copy was already running. That copy
                # owns the tray, so exit quietly: a dialog here would sit on screen
                # unclicked and hide the fact that the machine is already awake.
                logging.info("Wake task fired while Auto Shutdown was already running")
            else:
                QMessageBox.warning(
                    None,
                    "Auto Shutdown",
                    "Auto Shutdown đang chạy sẵn trong khay hệ thống.",
                )
            sys.exit(0)
        self.settings = load_settings()
        self.create_tray_icon()
        self.setup_tray()
        logging.info("Auto Shutdown started")

        self.countdown_panel = CountdownPanel()
        self.countdown_panel.apply_opacity(
            self.settings.get("panel_opacity", 100)
        )
        self.countdown_timer = QTimer()
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.tick_countdown)

        self.app.start_countdown = self.start_countdown
        self.app.cancel_countdown = self.cancel_countdown

        self.clean_ports_on_shutdown = False
        self.ports_closed = False
        self.shutdown_deadline = None
        self.popup = None

        # The app stays hidden in the tray. Open it from the tray icon.
        self.tray.showMessage(
            "Auto Shutdown",
            "Đang chạy ẩn trong khay hệ thống. Nhấp vào biểu tượng để mở.",
            QSystemTrayIcon.Information,
            3000,
        )

        if self.settings.get("open_on_launch", False):
            QTimer.singleShot(400, self.show_popup)

    def toggle_open_on_launch(self, enabled):
        self.settings["open_on_launch"] = bool(enabled)
        save_settings(self.settings)

    def create_tray_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(Token.accent))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 64, 64)
        painter.end()
        # Composite the same line clock used in the header, so tray and app match.
        painter = QPainter(pixmap)
        painter.drawPixmap(10, 10, 44, 44, icon_pixmap("clock", 44, "#FFFFFF"))
        painter.end()
        self.icon = QIcon(pixmap)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.icon, self.app)
        self.app.tray = self.tray

        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background: {Token.surface};
                border: 1px solid {Token.border};
                border-radius: {Token.radius_md}px;
                padding: {Token.space_2}px;
            }}
            QMenu::item {{
                padding: {Token.space_2}px {Token.space_4}px;
                color: #E2E8F0;
                border-radius: {Token.radius_sm}px;
            }}
            QMenu::item:selected {{
                background: {Token.accent};
                color: #FFFFFF;
            }}
            QMenu::separator {{
                height: 1px;
                background: {Token.border};
                margin: {Token.space_1}px {Token.space_2}px;
            }}
        """)

        open_action = menu.addAction(
            QIcon(icon_pixmap("clock", 16, "#E2E8F0")), "Đặt lịch tắt máy"
        )
        open_action.triggered.connect(self.show_popup)
        cancel_action = menu.addAction(
            QIcon(icon_pixmap("close", 16, "#E2E8F0")), "Hủy lịch hiện tại"
        )
        cancel_action.triggered.connect(self.cancel_countdown)
        clean_action = menu.addAction(
            QIcon(icon_pixmap("ban", 16, "#E2E8F0")), "Đóng cổng mạng đang mở"
        )
        clean_action.triggered.connect(self.quick_clean_ports)
        menu.addSeparator()

        self.launch_action = QAction("Mở cửa sổ khi khởi động", menu)
        self.launch_action.setCheckable(True)
        self.launch_action.setChecked(self.settings.get("open_on_launch", False))
        self.launch_action.triggered.connect(self.toggle_open_on_launch)
        menu.addAction(self.launch_action)

        quit_action = menu.addAction("Thoát ứng dụng")
        quit_action.triggered.connect(self.quit_app)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_clicked)
        self.tray.show()

    def tray_clicked(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.show_popup()

    def show_popup(self):
        # Reuse the existing window so an old instance never stays on screen.
        if self.popup is None:
            self.popup = ModernPopup()
        self.popup.show()
        self.popup.activateWindow()
        self.popup.raise_()

    def start_countdown(self, seconds, clean_ports_on_shutdown=False):
        self.clean_ports_on_shutdown = clean_ports_on_shutdown
        self.ports_closed = False
        self.countdown_panel.start(seconds, clean_ports_on_shutdown)
        self.countdown_timer.start()

    def tick_countdown(self):
        self.countdown_panel.update_countdown()

        if not self.clean_ports_on_shutdown or self.ports_closed:
            return

        remaining = QDateTime.currentDateTime().secsTo(
            self.countdown_panel.shutdown_deadline
        )
        if remaining > 25:
            return

        # Close the open ports right before the machine powers off.
        self.ports_closed = True
        entries = port_cleaner.list_bound_ports()
        killable = [entry for entry in entries if not entry.protected]
        killed, failed = port_cleaner.release_ports(killable)

        self.countdown_panel.status_label.setText(
            f"Đã đóng {len(killed)} cổng trước khi tắt"
            if killed
            else "Không có cổng ứng dụng để đóng"
        )
        self.tray.showMessage(
            "Đóng cổng trước khi tắt máy",
            f"Đã đóng {len(killed)} cổng mạng."
            + (f" {len(failed)} cổng không đóng được." if failed else ""),
            QSystemTrayIcon.Information,
            3000,
        )

        # Give closed processes a moment to cleanup before forcing shutdown.
        # This prevents race conditions where process cleanup races with power-off.
        import time
        time.sleep(1)

        # Ask Windows to cut the power now instead of at the buffered deadline.
        result = _run_quiet(["shutdown", "/s", "/t", "0"])
        code = result.returncode if result is not None else None
        logging.info("Port cleanup done, immediate shutdown returned %s", code)
        if code == 0:
            return
        if code == 1190:
            # 1190 = ERROR_SHUTDOWN_IS_SCHEDULED: the buffered deadline set in
            # set_shutdown() still stands, so the machine will power off anyway.
            self.countdown_panel.status_label.setText(
                "Đã dọn cổng · máy tắt theo lịch ban đầu"
            )
            return
        self.countdown_panel.status_label.setText(
            "Lỗi: không thể tắt máy (cần quyền admin)"
        )
        self.tray.showMessage(
            "Lỗi tắt máy",
            "Windows từ chối lệnh tắt máy. Cần chạy app với quyền admin.",
            QSystemTrayIcon.Critical,
            5000,
        )

    def quick_clean_ports(self):
        entries = port_cleaner.list_bound_ports()
        killable = [entry for entry in entries if not entry.protected]
        if not killable:
            self.tray.showMessage(
                "Đóng cổng mạng",
                "Không có cổng ứng dụng nào đang mở.",
                QSystemTrayIcon.Information,
                2500,
            )
            return
        if not confirm_port_cleanup(
            killable, self.popup if self.popup and self.popup.isVisible() else None
        ):
            return
        killed, failed = port_cleaner.release_ports(killable)
        logging.info("Quick port cleanup: %s closed, %s failed", len(killed), len(failed))
        message = f"Đã đóng {len(killed)} cổng mạng."
        if failed:
            message += f" {len(failed)} cổng không đóng được."
        self.tray.showMessage(
            "Đóng cổng mạng", message, QSystemTrayIcon.Information, 3000
        )

    def cancel_countdown(self):
        result = _run_quiet(["shutdown", "/a"])
        succeeded = result is not None and result.returncode == 0
        logging.info("Cancel shutdown returned %s", succeeded)
        self.countdown_timer.stop()
        self.countdown_panel.hide_panel()
        self.clean_ports_on_shutdown = False
        self.ports_closed = False
        if succeeded:
            message = "Lịch tắt máy đã được hủy."
            icon = QSystemTrayIcon.Information
        else:
            message = "Hiện không có lịch tắt máy đang hoạt động."
            icon = QSystemTrayIcon.Warning
        self.tray.showMessage("Trạng thái lịch tắt máy", message, icon, 2500)

    def quit_app(self):
        self.tray.hide()
        self.countdown_panel.hide_panel()
        self.app.quit()

    def run(self):
        if "--woke" in sys.argv:
            logging.info("Launched by the wake task")
            self.tray.showMessage(
                "Máy đã tự bật lại",
                "Máy đã tự bật theo lịch đã hẹn.",
                QSystemTrayIcon.Information,
                5000,
            )
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    setup_logging()
    install_excepthook()
    AutoShutdownApp().run()
