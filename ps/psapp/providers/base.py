from __future__ import annotations

import base64
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests
from PIL import Image, ImageOps


class ProviderError(RuntimeError):
    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


@dataclass
class EditRequest:
    image: Image.Image
    prompt: str
    negative_prompt: str = ""
    seed: int | None = None
    steps: int = 30
    cfg: float = 4.0
    candidates: int = 1


@dataclass
class EditResult:
    images: list[Image.Image]
    prompt: str
    seeds: list[int | None] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None

    @property
    def cost(self) -> float:
        return 0.0


class ImageEditProvider(ABC):
    name = "provider"
    cost_per_image = 0.0

    @abstractmethod
    def edit(self, request: EditRequest) -> EditResult:
        raise NotImplementedError

    def estimate_cost(self, count: int) -> float:
        return self.cost_per_image * max(count, 0)


def prepare_image(image: Image.Image, max_edge: int = 1536) -> Image.Image:
    if image.mode == "RGBA":
        canvas = Image.new("RGB", image.size, (255, 255, 255))
        canvas.paste(image, mask=image.getchannel("A"))
        image = canvas
    elif image.mode != "RGB":
        image = image.convert("RGB")

    width, height = image.size
    longest = max(width, height)
    if longest > max_edge:
        scale = max_edge / longest
        size = (max(1, round(width * scale)), max(1, round(height * scale)))
        image = image.resize(size, Image.LANCZOS)
    return image


def to_data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def decode_b64_image(value: str) -> Image.Image:
    if value.startswith("data:"):
        value = value.split(",", 1)[-1]
    raw = base64.b64decode(value)
    image = Image.open(io.BytesIO(raw))
    image.load()
    return ImageOps.exif_transpose(image).convert("RGB")


def download_image(
    session: requests.Session, url: str, timeout: int = 120
) -> Image.Image:
    response = session.get(url, timeout=(15, timeout))
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content))
    image.load()
    return ImageOps.exif_transpose(image).convert("RGB")


def build_session(
    proxy: str = "", headers: dict[str, str] | None = None
) -> requests.Session:
    session = requests.Session()
    if headers:
        session.headers.update(headers)
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})
    return session


def error_detail(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            message = data.get("message") or data.get("detail") or data.get("error")
            code = data.get("code")
            if message:
                return f"{code}: {message}" if code else str(message)
        return str(data)[:500]
    except ValueError:
        return (response.text or "").strip()[:500]
