import threading

import numpy as np


class OcrEngine:
    """rapidocr 封装：把图片交给 OCR 模型，返回文字框信息与中心坐标。

    无需 GPU，文档/菜单文字定位稳定，可作为“视觉识别给坐标→鼠标操作”坐标来源。
    """

    def __init__(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
        except Exception as e:
            raise RuntimeError(
                f"OCR 依赖加载失败: {type(e).__name__}: {e}"
            ) from e
        self._engine = RapidOCR()
        self._lock = threading.Lock()

    def detect(self, img):
        """识别一张图。img 为 HxWx3 numpy(RGB)。

        返回快速检索结构列表：
            [{"text": str, "score": float,
              "box": (x, y, w, h),          # 外接框（相对本图）
              "center": (cx, cy)}]          # 中心点（相对本图）
        无文字时返回空列表。
        """
        if img is None or img.size == 0:
            return []
        with self._lock:
            res, _ = self._engine(np.asarray(img))
        items = []
        if not res:
            return items
        for box_pts, text, score in res:
            try:
                xs = [p[0] for p in box_pts]
                ys = [p[1] for p in box_pts]
            except (TypeError, KeyError):
                continue
            x, y = int(min(xs)), int(min(ys))
            w, h = int(max(xs) - x), int(max(ys) - y)
            items.append({
                "text": str(text),
                "score": float(score),
                "box": (x, y, w, h),
                "center": (x + w // 2, y + h // 2),
            })
        return items

    def find(self, img, keywords, min_score=0.5, origin=(0, 0), full_match=False):
        """在裁剪图 img 中寻找关键词（图片内文字），返回绝对坐标列表。

        keywords: 可匹配的文本列表（任意一个命中即算）。
        origin:   本图左上角在全屏中的 (x0, y0)，返回坐标为全屏绝对坐标。
        full_match: True 表示文本需完全等于关键词之一；False 表示包含即可。
        返回: [{"text","score","center":(cx,cy),"box"}...]（绝对坐标），找不到为空列表。
        """
        hit = []
        for item in self.detect(img):
            text = item["text"].strip()
            matched = any(
                (text == kw) if full_match else (kw in text)
                for kw in keywords
            )
            if not matched or item["score"] < min_score:
                continue
            cx, cy = item["center"]
            item["center"] = (cx + origin[0], cy + origin[1])
            item["box"] = (
                item["box"][0] + origin[0],
                item["box"][1] + origin[1],
                item["box"][2],
                item["box"][3],
            )
            hit.append(item)
        return hit