import time

import numpy as np

try:
    import dxcam
except ImportError:
    dxcam = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

_CAM = None


def _pil_frame(bbox=None):
    if ImageGrab is None:
        raise RuntimeError("缺少依赖 Pillow，请先运行: pip install pillow")
    img = ImageGrab.grab(bbox=bbox)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.asarray(img)


def _camera():
    global _CAM
    if _CAM is None:
        if dxcam is None:
            raise RuntimeError("缺少依赖 dxcam，请先运行: pip install dxcam")
        _CAM = dxcam.create(output_idx=0, output_color="RGB")
    return _CAM


def _dxcam_frame(max_retries=5, retry_delay=0.1):
    cam = _camera()
    last = None
    for _ in range(max_retries):
        frame = cam.grab()
        if frame is not None:
            return np.asarray(frame)
        last = frame
        time.sleep(retry_delay)
    raise RuntimeError("dxcam 抓屏失败（连续返回 None）")


def grab(max_retries=3, retry_delay=0.1):
    """抓取整屏（主屏）。优先 PIL(GDI)，失败时回退 dxcam。返回 HxWx3 numpy(RGB)。"""
    for attempt in range(max_retries):
        try:
            return _pil_frame()
        except Exception as pil_err:
            try:
                return _dxcam_frame()
            except Exception as dx_err:
                time.sleep(retry_delay)
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"抓屏失败 PIL: {type(pil_err).__name__}: {pil_err}；"
                        f"dxcam: {type(dx_err).__name__}: {dx_err}"
                    )


def crop(x0, y0, w, h, max_retries=3, retry_delay=0.1):
    """抓取指定区域（PIL bbox 直接裁剪，仅主屏）。返回 HxWx3 numpy(RGB)。"""
    x0, y0, w, h = int(x0), int(y0), int(w), int(h)
    if w < 1 or h < 1:
        raise ValueError("裁剪区域非法")
    for attempt in range(max_retries):
        try:
            return _pil_frame(bbox=(x0, y0, x0 + w, y0 + h))
        except Exception as pil_err:
            try:
                frame = _dxcam_frame()
                fh, fw = frame.shape[:2]
                x0c = max(0, min(x0, fw - 1))
                y0c = max(0, min(y0, fh - 1))
                wc = min(w, fw - x0c)
                hc = min(h, fh - y0c)
                if wc < 1 or hc < 1:
                    raise ValueError("裁剪区域非法")
                return frame[y0c : y0c + hc, x0c : x0c + wc]
            except Exception as dx_err:
                time.sleep(retry_delay)
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"抓屏失败 PIL: {type(pil_err).__name__}: {pil_err}；"
                        f"dxcam: {type(dx_err).__name__}: {dx_err}"
                    )


def screen_size():
    frame = grab()
    return frame.shape[1], frame.shape[0]
