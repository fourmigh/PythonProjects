@echo off
chcp 65001 >nul
cd /d "%~dp0"
pyinstaller --noconfirm --onefile --windowed --name "电源助手" ^
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
rem 打包成功：清理临时生成的文件（build 目录、自动生成的 spec、__pycache__）
if exist "%~dp0build" rmdir /s /q "%~dp0build"
if exist "%~dp0*.spec" del /q "%~dp0*.spec"
if exist "%~dp0__pycache__" rmdir /s /q "%~dp0__pycache__"
if exist "%~dp0..\ai_core\__pycache__" rmdir /s /q "%~dp0..\ai_core\__pycache__"
echo 打包完成: %~dp0dist\电源助手.exe
pause
