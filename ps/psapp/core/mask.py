from __future__ import annotations

from PIL import Image, ImageFilter


def ensure_mask(mask: Image.Image, size: tuple[int, int]) -> Image.Image:
    if mask.mode != "L":
        mask = mask.convert("L")
    if mask.size != size:
        mask = mask.resize(size, Image.LANCZOS)
    return mask


def has_mask(mask: Image.Image | None) -> bool:
    return mask is not None and ensure_mask(mask, mask.size).getbbox() is not None


def highlight(
    image: Image.Image,
    mask: Image.Image,
    color: tuple[int, int, int] = (255, 64, 64),
    alpha: float = 0.45,
) -> Image.Image:
    image = image.convert("RGB")
    mask = ensure_mask(mask, image.size)
    if mask.getbbox() is None:
        return image.copy()
    alpha_map = mask.point(lambda value: int(value * alpha))
    overlay = Image.new("RGB", image.size, color)
    return Image.composite(overlay, image, alpha_map)


def paste_back(
    original: Image.Image,
    generated: Image.Image,
    mask: Image.Image,
    feather: int = 6,
) -> Image.Image:
    original = original.convert("RGB")
    generated = generated.convert("RGB").resize(original.size, Image.LANCZOS)
    mask = ensure_mask(mask, original.size)
    if feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
    return Image.composite(generated, original, mask)


def mask_bbox(mask: Image.Image) -> tuple[int, int, int, int] | None:
    return ensure_mask(mask, mask.size).getbbox()
