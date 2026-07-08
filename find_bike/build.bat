@echo off
cd /d "%~dp0"
echo Building BikeDetector.exe ...
pyinstaller --clean BikeDetector.spec
if %ERRORLEVEL% neq 0 (
    echo Build FAILED!
    pause
    exit /b 1
)
echo.
echo Build SUCCESS! Output: dist\BikeDetector.exe
pause
