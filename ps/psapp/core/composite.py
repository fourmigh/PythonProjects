from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


def load_image(path: str | Path) -> Image.Image:
    image = Image.open(path)
    image.load()
    return ImageOps.exif_transpose(image)


def resize_to_fit(image: Image.Image, max_edge: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_edge:
        return image
    scale = max_edge / longest
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(size, Image.LANCZOS)


def save_image(image: Image.Image, path: str | Path, quality: int = 95) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        image.convert("RGB").save(path, "JPEG", quality=quality, optimize=True)
    elif suffix == ".webp":
        image.save(path, "WEBP", quality=quality)
    else:
        image.save(path, "PNG", optimize=True)
    return path


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError("颜色格式应为 #RRGGBB")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    new_size = (max(1, round(src_w * scale)), max(1, round(src_h * scale)))
    resized = image.resize(new_size, Image.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def compose_background(
    foreground: Image.Image,
    background: Image.Image | tuple[int, int, int],
) -> Image.Image:
    foreground = foreground.convert("RGBA")
    size = foreground.size
    if isinstance(background, tuple):
        canvas = Image.new("RGBA", size, (*background, 255))
    else:
        canvas = cover_resize(background.convert("RGB"), size).convert("RGBA")
    canvas.alpha_composite(foreground)
    return canvas.convert("RGB")


def side_by_side(
    left: Image.Image,
    right: Image.Image,
    gap: int = 16,
    background: tuple[int, int, int] = (30, 31, 34),
) -> Image.Image:
    left = left.convert("RGB")
    right = right.convert("RGB")
    height = max(left.height, right.height)

    def pad(image: Image.Image) -> Image.Image:
        canvas = Image.new("RGB", (image.width, height), background)
        canvas.paste(image, (0, (height - image.height) // 2))
        return canvas

    left = pad(left)
    right = pad(right)
    result = Image.new("RGB", (left.width + gap + right.width, height), background)
    result.paste(left, (0, 0))
    result.paste(right, (left.width + gap, 0))
    return result
