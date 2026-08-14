"""可复用的大模型/视觉识别相关代码。

- capture.py: 屏幕抓取（PIL GDI 为主，dxcam 回退）
- ocr.py: rapidocr 文字识别（视觉识别模型，提供坐标）
"""

from .capture import crop, grab, screen_size
from .ocr import OcrEngine

__all__ = ["crop", "grab", "screen_size", "OcrEngine"]