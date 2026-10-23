from __future__ import annotations

import base64
import io
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from psapp.ui.clipboard import (
    extract_clipboard,
    has_clipboard_image,
    qimage_to_pil,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeClipboard:
    def __init__(self, mime: QMimeData, image: QImage | None = None, text: str = ""):
        self._mime = mime
        self._image = image
        self._text = text

    def mimeData(self) -> QMimeData:
        return self._mime

    def image(self) -> QImage:
        return self._image if self._image is not None else QImage()

    def text(self) -> str:
        return self._text


def make_qimage() -> QImage:
    image = QImage(20, 10, QImage.Format.Format_RGB32)
    image.fill(QColor(10, 20, 30))
    return image


def test_qimage_to_pil(qapp) -> None:
    image = qimage_to_pil(make_qimage())
    assert image is not None
    assert image.size == (20, 10)
    assert image.convert("RGB").getpixel((0, 0)) == (10, 20, 30)


def test_extract_bitmap(qapp) -> None:
    mime = QMimeData()
    qimage = make_qimage()
    mime.setImageData(qimage)
    image, path = extract_clipboard(FakeClipboard(mime, image=qimage))
    assert path is None
    assert image is not None
    assert image.size == (20, 10)


def test_extract_local_file_url(qapp, tmp_path) -> None:
    target = tmp_path / "clip.png"
    Image.new("RGB", (12, 9), (200, 100, 50)).save(target)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(target))])
    image, path = extract_clipboard(FakeClipboard(mime))
    assert image is None
    assert path == target


def test_extract_html_data_url(qapp) -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 8), (1, 2, 3)).save(buffer, "PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    html = f'<img src="data:image/png;base64,{encoded}">'
    mime = QMimeData()
    mime.setHtml(html)
    image, path = extract_clipboard(FakeClipboard(mime))
    assert path is None
    assert image is not None
    assert image.size == (16, 8)


def test_extract_text_path(qapp, tmp_path) -> None:
    target = tmp_path / "path.jpg"
    Image.new("RGB", (8, 8), (10, 10, 10)).save(target)
    mime = QMimeData()
    mime.setText(str(target))
    image, path = extract_clipboard(FakeClipboard(mime, text=str(target)))
    assert image is None
    assert path == target


def test_extract_plain_text(qapp) -> None:
    mime = QMimeData()
    mime.setText("hello world")
    image, path = extract_clipboard(FakeClipboard(mime, text="hello world"))
    assert image is None
    assert path is None


def test_has_clipboard_image(qapp) -> None:
    mime = QMimeData()
    mime.setText("hello")
    assert not has_clipboard_image(FakeClipboard(mime, text="hello"))

    bitmap_mime = QMimeData()
    qimage = make_qimage()
    bitmap_mime.setImageData(qimage)
    assert has_clipboard_image(FakeClipboard(bitmap_mime, image=qimage))
