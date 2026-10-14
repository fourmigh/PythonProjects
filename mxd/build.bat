@echo off
cd /d "%~dp0"

echo ============================================
echo [1/3] Installing build dependencies (pyinstaller, pillow) ...
echo ============================================
python -m pip install --disable-pip-version-check pyinstaller pillow
if %ERRORLEVEL% neq 0 (
    echo.
    echo Failed to install build dependencies!
    pause
    exit /b 1
)

echo ============================================
echo [2/3] Generating icon ...
echo ============================================
if not exist "assets\app.ico" (
    python make_icon.py
)

echo ============================================
echo [3/3] Building MxdTool.exe ...
echo ============================================
python -m PyInstaller --clean --noconfirm MxdTool.spec
if %ERRORLEVEL% neq 0 (
    echo.
    echo Build FAILED!
    pause
    exit /b 1
)

echo.
echo Build SUCCESS! Output: dist\MxdTool.exe
pause
