from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice, QUrl
from PySide6.QtGui import QClipboard, QImage

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

_DATA_URL_RE = re.compile(
    r"data:image/[a-zA-Z0-9.+-]+;base64,([A-Za-z0-9+/=\s]+)", re.IGNORECASE
)
_FILE_URL_RE = re.compile(r'file:///[^"\'\s>]+', re.IGNORECASE)


def qimage_to_pil(qimage: QImage | None) -> Image.Image | None:
    if qimage is None or qimage.isNull():
        return None
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    try:
        if not qimage.save(buffer, "PNG"):
            return None
        data = bytes(buffer.data())
    finally:
        buffer.close()
    if not data:
        return None
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


def image_from_html(html_text: str) -> Image.Image | None:
    if not html_text:
        return None

    match = _DATA_URL_RE.search(html_text)
    if match:
        payload = re.sub(r"\s+", "", match.group(1))
        try:
            raw = base64.b64decode(payload)
            image = Image.open(io.BytesIO(raw))
            image.load()
            return image
        except Exception:
            pass

    for raw_url in _FILE_URL_RE.findall(html_text):
        local = QUrl(raw_url.rstrip("\"'")).toLocalFile()
        if not local:
            continue
        path = Path(local)
        if path.suffix.lower() in IMAGE_SUFFIXES and path.exists():
            try:
                image = Image.open(path)
                image.load()
                return image
            except Exception:
                continue
    return None


def _text_image_path(text: str) -> Path | None:
    value = text.strip().strip('"').strip("'")
    if not value:
        return None
    if value.lower().startswith("file://"):
        value = QUrl(value).toLocalFile()
    if not value:
        return None
    try:
        path = Path(value)
        if path.suffix.lower() in IMAGE_SUFFIXES and path.exists():
            return path
    except OSError:
        return None
    return None


def extract_clipboard(
    clipboard: QClipboard,
) -> tuple[Image.Image | None, Path | None]:
    mime = clipboard.mimeData()
    if mime is None:
        return None, None

    if mime.hasUrls():
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() in IMAGE_SUFFIXES and path.exists():
                return None, path

    if mime.hasImage():
        image = qimage_to_pil(clipboard.image())
        if image is not None:
            return image, None

    if mime.hasHtml():
        image = image_from_html(mime.html())
        if image is not None:
            return image, None

    if mime.hasText():
        path = _text_image_path(clipboard.text())
        if path is not None:
            return None, path

    return None, None


def has_clipboard_image(clipboard: QClipboard) -> bool:
    mime = clipboard.mimeData()
    if mime is None:
        return False
    if mime.hasImage() and not clipboard.image().isNull():
        return True
    if mime.hasUrls():
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            if Path(url.toLocalFile()).suffix.lower() in IMAGE_SUFFIXES:
                return True
    if mime.hasHtml():
        html_text = mime.html().lower()
        if "data:image/" in html_text or "file:///" in html_text:
            return True
    if mime.hasText() and _text_image_path(clipboard.text()) is not None:
        return True
    return False
