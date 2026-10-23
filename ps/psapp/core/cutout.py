from __future__ import annotations

import hashlib
import os
from pathlib import Path

import requests
from PIL import Image, ImageFilter

MODEL_FILENAME = "u2net.onnx"
MODEL_MD5 = "60024c5c889badc19c04ad937298a77b"
OFFICIAL_URL = (
    "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
)
MIRRORS = (
    f"https://gh-proxy.com/{OFFICIAL_URL}",
    f"https://ghproxy.net/{OFFICIAL_URL}",
    OFFICIAL_URL,
)

_session = None


def available() -> bool:
    try:
        import rembg  # noqa: F401
    except ImportError:
        return False
    return True


def model_path() -> Path:
    try:
        from rembg.sessions.u2net import U2netSession

        return Path(U2netSession.model_dir()) / MODEL_FILENAME
    except Exception:
        return Path.home() / ".rembg" / "models" / "u2net" / MODEL_FILENAME


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_model(progress=None) -> Path:
    target = model_path()
    if target.exists():
        try:
            if _md5(target) == MODEL_MD5:
                return target
        except OSError:
            pass

    target.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for url in MIRRORS:
        temp = target.with_suffix(".part")
        try:
            with requests.get(url, stream=True, timeout=(15, 90)) as response:
                response.raise_for_status()
                total = int(response.headers.get("Content-Length", "0") or 0)
                done = 0
                with temp.open("wb") as handle:
                    for chunk in response.iter_content(1024 * 256):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        done += len(chunk)
                        if progress is not None and total:
                            percent = min(99, done * 100 // total)
                            progress(f"正在下载抠图模型… {percent}%")
            if _md5(temp) != MODEL_MD5:
                errors.append(f"{url} 校验失败")
                temp.unlink(missing_ok=True)
                continue
            os.replace(temp, target)
            if progress is not None:
                progress("抠图模型下载完成")
            return target
        except Exception as exc:
            errors.append(f"{url} 下载失败：{exc}")
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    raise RuntimeError(
        "抠图模型下载失败。请手动下载 u2net.onnx 并放到：\n"
        f"{target}\n\n"
        "可用地址：\n"
        f"{MIRRORS[0]}\n"
        f"{MIRRORS[1]}\n\n"
        + "\n".join(errors[-3:])
    )


def _get_session(progress=None):
    global _session
    if _session is not None:
        return _session
    ensure_model(progress)
    from rembg import new_session

    _session = new_session("u2net")
    return _session


def remove_background(image: Image.Image, progress=None) -> Image.Image:
    try:
        from rembg import remove
    except ImportError as exc:
        raise RuntimeError(
            "未安装 rembg，请先运行：pip install rembg onnxruntime"
        ) from exc

    session = _get_session(progress)
    result = remove(image.convert("RGBA"), session=session)
    if result.mode != "RGBA":
        result = result.convert("RGBA")
    alpha = result.getchannel("A").filter(ImageFilter.GaussianBlur(radius=1))
    result.putalpha(alpha)
    return result
