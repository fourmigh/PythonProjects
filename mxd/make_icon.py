"""生成应用图标 assets/app.ico（深蓝底 + 白色 MXD），构建期使用。

运行：python make_icon.py
依赖：pillow
"""

import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "assets")
SIZE = 256
BG = (30, 58, 138, 255)      # #1E3A8A 深蓝
FG = (255, 255, 255, 255)    # 白
TEXT = "MXD"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def find_font(px):
    win = os.environ.get("WINDIR", r"C:\Windows")
    for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf", "segoeui.ttf"):
        path = os.path.join(win, "Fonts", name)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, px)
            except OSError:
                continue
    return ImageFont.load_default()


def make():
    os.makedirs(OUT_DIR, exist_ok=True)
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 8
    draw.rounded_rectangle([margin, margin, SIZE - margin, SIZE - margin], radius=48, fill=BG)

    # 自动缩放字号，使文字占宽度约 78%
    font = find_font(80)
    target = int(SIZE * 0.78)
    for px in range(120, 20, -2):
        font = find_font(px)
        bbox = draw.textbbox((0, 0), TEXT, font=font)
        if bbox[2] - bbox[0] <= target:
            break

    bbox = draw.textbbox((0, 0), TEXT, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((SIZE - tw) / 2 - bbox[0], (SIZE - th) / 2 - bbox[1]), TEXT, font=font, fill=FG)

    ico = os.path.join(OUT_DIR, "app.ico")
    png = os.path.join(OUT_DIR, "app.png")
    img.save(ico, sizes=SIZES)
    img.save(png)
    print("wrote %s" % ico)
    print("wrote %s" % png)


if __name__ == "__main__":
    make()
