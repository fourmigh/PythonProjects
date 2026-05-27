# 我是B站的UP主：偶尔有点小迷糊
# 代码讲解视频：https://www.bilibili.com/video/BV1mq4y1n7aE/
# 转载请保留此信息

import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    os.system('pip install pillow -i https://pypi.mirrors.ustc.edu.cn/simple/')
    from PIL import Image, ImageDraw, ImageFont


def list_system_fonts():
    font_dir = r"/mnt/c/Windows/Fonts"
    fonts = [f for f in sorted(os.listdir(font_dir))
             if f.lower().endswith(('.ttf', '.otf', '.ttc'))]
    return fonts, font_dir


def calc_density(font_path, chars, font_size=40):
    font = ImageFont.truetype(font_path, font_size)
    densities = []
    for char in chars:
        bb = font.getbbox(char)
        if not bb or bb[2] == 0 or bb[3] == 0:
            continue
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        if w <= 0 or h <= 0:
            continue
        img = Image.new('L', (w, h), 255)
        draw = ImageDraw.Draw(img)
        draw.text((-bb[0], -bb[1]), char, fill=0, font=font)
        pixels = list(img.get_flattened_data())
        black = sum(1 for p in pixels if p < 128)
        densities.append((char, black / len(pixels)))
    densities.sort(key=lambda x: x[1])
    return [c for c, _ in densities]


def make_mosaic(img_src, sorted_chars, font_path, char_px, label=""):
    """逐像素生成字符马赛克图"""
    w, h = img_src.size
    out_w = w * char_px
    out_h = h * char_px

    out = img_src.resize((out_w, out_h), Image.NEAREST)
    draw = ImageDraw.Draw(out)
    font = ImageFont.truetype(font_path, char_px)

    # 计算字符居中偏移
    ox = oy = 0
    for c in sorted_chars:
        bb = font.getbbox(c)
        if bb and bb[2] > 0 and bb[3] > 0:
            ox = max((char_px - (bb[2] - bb[0])) // 2, 0)
            oy = max((char_px - (bb[3] - bb[1])) // 2, 0)
            break

    n = len(sorted_chars)
    for y in range(h):
        for x in range(w):
            pixel = img_src.getpixel((x, y))
            if isinstance(pixel, int):
                gray = pixel
            else:
                gray = (pixel[0] + pixel[1] + pixel[2]) / 3
            ci = int((255 - gray) / 255 * (n - 1))
            tc = (0, 0, 0) if gray > 128 else (255, 255, 255)
            draw.text((x * char_px + ox, y * char_px + oy),
                      sorted_chars[ci], fill=tc, font=font)
        print(f"\r{label} {y + 1}/{h} 行 ({((y + 1) / h * 100):.0f}%)",
              end='', flush=True)
    print()
    return out


def make_auto(img_src, sorted_chars, font_path, char_px, label=""):
    """先降采样再生成字符图，输出 ≈ 原图尺寸"""
    w, h = img_src.size
    bw = max(w // char_px, 1)
    bh = max(h // char_px, 1)
    img_small = img_src.resize((bw, bh), Image.LANCZOS)

    out_w = bw * char_px
    out_h = bh * char_px
    out = img_small.resize((out_w, out_h), Image.NEAREST)
    draw = ImageDraw.Draw(out)
    font = ImageFont.truetype(font_path, char_px)

    ox = oy = 0
    for c in sorted_chars:
        bb = font.getbbox(c)
        if bb and bb[2] > 0 and bb[3] > 0:
            ox = max((char_px - (bb[2] - bb[0])) // 2, 0)
            oy = max((char_px - (bb[3] - bb[1])) // 2, 0)
            break

    n = len(sorted_chars)
    for y in range(bh):
        for x in range(bw):
            pixel = img_small.getpixel((x, y))
            if isinstance(pixel, int):
                gray = pixel
            else:
                gray = (pixel[0] + pixel[1] + pixel[2]) / 3
            ci = int((255 - gray) / 255 * (n - 1))
            tc = (0, 0, 0) if gray > 128 else (255, 255, 255)
            draw.text((x * char_px + ox, y * char_px + oy),
                      sorted_chars[ci], fill=tc, font=font)
        print(f"\r{label} {y + 1}/{bh} 行 ({((y + 1) / bh * 100):.0f}%)",
              end='', flush=True)
    print()
    return out, (bw, bh)


def main():
    fonts, font_dir = list_system_fonts()
    print(f"找到 {len(fonts)} 个字体文件\n")
    for i, f in enumerate(fonts):
        print(f"  {i + 1}. {f}")

    idx = int(input("\n选择字体编号: ")) - 1
    font_path = os.path.join(font_dir, fonts[idx])
    font_name = os.path.splitext(fonts[idx])[0]

    image_path = input("图片路径: ").strip()
    txt = input("字符集: ").strip()
    if not txt:
        print("字符集不能为空")
        return

    print("\n正在计算字符密度...")
    sorted_chars = calc_density(font_path, txt)
    if not sorted_chars:
        print("错误：所选字体中没有可用的字符")
        return
    print(f"排序后: {''.join(sorted_chars)}")

    img_src = Image.open(image_path).convert('RGB')
    w, h = img_src.size

    char_px = int(input(f"\n字符像素 (每个字符占多少像素, 建议 8~16, 默认 8): ").strip() or "8")
    if char_px < 4:
        char_px = 4

    # 全尺寸图预估
    full_mp = w * h * char_px * char_px / (1024 * 1024)
    print(f"\n全尺寸图: {w * char_px}×{h * char_px} = {full_mp:.0f}M 像素")
    if full_mp > 200:
        if input(f"全尺寸图较大 ({full_mp:.0f}M 像素)，继续？(y/n): ").strip().lower() != 'y':
            print("已取消")
            return

    # 1. 全尺寸 B站法
    print(f"\n1/3 生成全尺寸字符画...")
    full = make_mosaic(img_src, sorted_chars, font_path, char_px, "全尺寸")

    # 2. 缩回原图尺寸
    print(f"2/3 缩回原图尺寸...")
    scaled = full.resize((w, h), Image.LANCZOS)

    # 3. 原大字符画
    print(f"3/3 生成原大字符画...")
    auto, (bw, bh) = make_auto(img_src, sorted_chars, font_path, char_px, "原大")

    # 保存
    base = os.path.splitext(os.path.basename(image_path))[0]
    out_dir = os.path.dirname(image_path)

    paths = [
        os.path.join(out_dir, f"{base}_{font_name}_full.png"),
        os.path.join(out_dir, f"{base}_{font_name}_scaled.png"),
        os.path.join(out_dir, f"{base}_{font_name}_auto.png"),
    ]
    full.save(paths[0])
    scaled.save(paths[1])
    auto.save(paths[2])
    print("已保存:")
    print(f"  {paths[0]}  ({w * char_px}×{h * char_px})")
    print(f"  {paths[1]}  ({w}×{h})")
    print(f"  {paths[2]}  ({bw * char_px}×{bh * char_px})")


if __name__ == '__main__':
    main()
