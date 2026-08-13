@echo off
chcp 65001 >nul
cd /d "%~dp0"
pyinstaller --noconfirm --onefile --windowed --name "关机助手" ^
  --paths "%~dp0.." ^
  --collect-all rapidocr_onnxruntime ^
  --collect-all dxcam ^
  --exclude-module torch ^
  --exclude-module tensorflow ^
  --runtime-hook "%~dp0rthook_onnx.py" ^
  --add-binary "%WINDIR%\System32\msvcp140.dll;." ^
  gui.py
if errorlevel 1 (
  echo 打包失败
  pause
  exit /b 1
)
echo 打包完成: %~dp0dist\关机助手.exe
pause
