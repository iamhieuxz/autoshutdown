# AutoShutdown v2.0.1 - Patch Release

## What's Fixed

### 🐛 Bug Fixes
- **Fixed missing `scale` variable** in icon rendering that caused crashes on startup
- **Improved temp directory error handling** - gracefully falls back if temp folder not accessible
- **Enhanced resource cleanup** on startup errors

### ✨ Improvements
- **Main menu now shows on launch by default** - better user experience (can be disabled in settings via `open_on_launch: false`)
- **Faster startup** - reduced initialization delay from 400ms to 200ms
- **Better error recovery** - app continues running even if temp directory unavailable

## What's Included

All fixes and features from **v2.0** plus:
- ✅ 11 critical bug fixes (timezone, injection, race conditions, UI/UX)
- ✅ Quality improvements (error handling, caching, resilience)
- ✅ New: Menu displays on launch
- ✅ New: Fallback temp directory handling

## Download

**AutoShutdown.exe** - Standalone, no Python required. Just run it!

## Installation

1. Download `AutoShutdown.exe`
2. Double-click to run
3. Menu opens automatically
4. Configure shutdown/port cleaning as needed

## Changes in v2.0.1

```
f8ee5ca feat: show main menu on launch by default (open_on_launch = True)
a6f62da fix: missing scale variable in icon_pixmap
```

## Building

To rebuild from source:
```bash
pip install -r requirements.txt
pyinstaller AutoShutdown.spec --distpath dist --workpath build
```

## Compatibility

- Windows 7+
- No Python installation needed
- Supports Windows 10/11 fully

## Known Limitations

None at this release.

## Support

Report issues: https://github.com/iamhieuxz/autoshutdown/issues

---

**Previous Release:** v2.0 (Critical security fixes, reliability improvements)
