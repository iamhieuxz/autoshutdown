# AutoShutdown v2.0 - Release Notes

## Changelog

### 🔧 Major Bug Fixes (Critical)

- **#6 - Timezone Handling**: Fixed datetime comparison between naive and timezone-aware datetimes. All timezone-aware times now convert to naive local time for consistent comparison.

- **#3 - PowerShell Injection**: Secured command execution by using base64 encoding for executable paths and arguments instead of string interpolation. Prevents shell injection attacks.

- **#1 - Race Condition**: Added 1-second grace period after closing ports before triggering immediate shutdown. Prevents race conditions where closed processes haven't finished cleanup.

- **#2 - Uninitialized Controls**: Added defensive null checks for `time_edit` widget. Shows error dialog if initialization fails instead of crashing.

### 🎨 UI/UX Improvements

- **Port List**: Fixed empty state handling - now clears all items when no ports are open, preventing confusing empty group headers.

- **Process Names**: Sanitize process names to remove control characters and newlines that break UI rendering.

- **Panel Positioning**: Enhanced validation to ensure entire countdown panel fits within screen bounds, not just the corner.

- **Clock Input**: Added validation for time spinners - hour clamped to [0-23], minute to [0-59].

### 🛠️ Quality & Resilience

- **psutil Import**: Explicit error handling for optional psutil dependency.

- **JSON Parsing**: Validate that required keys (`boundary`, `wake_to_run`) exist before accessing.

- **Settings Persistence**: Better error handling - differentiate between first run (no file) vs corrupted settings.

- **Timeout Logging**: Subprocess timeouts now logged separately with command info.

- **Icon Cache**: Limited cache to 100 entries with FIFO eviction to prevent memory leaks.

- **PowerShell Retry**: Automatic retry on PowerShell failure (e.g., service restart).

### 📦 Build & Distribution

- Created PyInstaller spec file for reproducible builds
- Generated standalone AutoShutdown.exe (37.4 MB)
- All tests pass with no regressions

### 🧪 Testing

- ✅ `test_wake_scheduler.py` - All timezone and JSON parsing tests pass
- ✅ `test_port_cleaner.py` - All psutil and port protection tests pass
- ✅ `test_auto_shutdown.py` - All UI/UX logic tests pass

## Files Changed

- `wake_scheduler.py` - 3 major fixes (timezone, injection, retry)
- `port_cleaner.py` - 2 fixes (psutil, logging)
- `AutoShutdown.py` - 9 fixes (race, init, UI, cache, settings)
- `test_wake_scheduler.py` - Updated timezone test
- New: `AutoShutdown.spec` - PyInstaller build configuration

## Installation

### From EXE
Download `AutoShutdown.exe` from the release assets and run directly. No Python installation required.

### From Source
```bash
git clone https://github.com/username/autoshutdown.git
cd autoshutdown
pip install -r requirements.txt
python AutoShutdown.py
```

## Building

To rebuild the executable:
```bash
pip install -r requirements.txt
pyinstaller AutoShutdown.spec --distpath dist --workpath build
```

Output: `dist/AutoShutdown.exe`
