@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================
echo  翻译对照工具 exe 打包
echo  用法: build_exe.bat [online^|offline^|all]
echo   online  = 仅在线翻译（体积小）
echo   offline = 仅离线翻译（体积大，无需联网）
echo   all     = 两个都打包（默认）
echo ============================================
echo.
python build_exe.py %1
pause