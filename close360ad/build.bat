@echo off
chcp 65001 >nul
echo [1/3] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%

echo [2/3] Building icon...
python -c "
from PIL import Image, ImageDraw
img = Image.new('RGBA', (32, 32), (0,0,0,0))
d = ImageDraw.Draw(img)
d.ellipse([2,2,30,30], fill='#CC0000', outline='#880000', width=2)
d.line([10,10,24,24], fill='white', width=4)
d.line([24,10,10,24], fill='white', width=4)
img.save('icon.ico', format='ICO', sizes=[(32,32)])
"

echo [3/3] Building exe...
pyinstaller --onefile --noconsole --icon=icon.ico --name=Close360Ad --clean main.py
if %errorlevel% equ 0 (
    echo.
    echo Build success! Output: dist\Close360Ad.exe
)
