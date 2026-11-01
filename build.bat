@echo off
echo ============================================
echo   Building Auto Shutdown...
echo ============================================
echo.

pip install -r requirements.txt

if not exist icon.ico (
    echo Generating icon...
    python make_icon.py
)

echo.
echo Building executable...
pyinstaller --onefile --windowed --icon=icon.ico --name="AutoShutdown" --clean --hidden-import=port_cleaner --hidden-import=wake_scheduler AutoShutdown.py

echo.
echo ============================================
echo   Done! Executable: dist\AutoShutdown.exe
echo ============================================
pause
