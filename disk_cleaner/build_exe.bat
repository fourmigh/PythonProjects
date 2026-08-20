@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  DiskCleaner 打包脚本 (PyInstaller)
echo ============================================
python -m pip install -r requirements.txt --quiet
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DiskCleaner disk_cleaner.py
if errorlevel 1 (
    echo.
    echo Build FAILED. See log above.
    pause
    exit /b 1
)
echo.
echo Done: %~dp0dist\DiskCleaner.exe
echo.
pause
