from __future__ import annotations

import base64
import io

from PIL import Image, ImageDraw

from psapp.config import AppConfig
from psapp.core.composite import compose_background, hex_to_rgb, side_by_side
from psapp.core.history import SessionHistory
from psapp.core.mask import highlight, paste_back
from psapp.providers.base import prepare_image, to_data_url
from psapp.providers.siliconflow import SiliconFlowProvider
from psapp.providers.zhipu import PromptRewriter


def make_mask(size=(40, 40), box=(10, 10, 29, 29)) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    return mask


def test_paste_back_keeps_outside_pixels() -> None:
    original = Image.new("RGB", (40, 40), (0, 0, 255))
    generated = Image.new("RGB", (40, 40), (255, 0, 0))
    result = paste_back(original, generated, make_mask(), feather=0)
    assert result.getpixel((2, 2)) == (0, 0, 255)
    assert result.getpixel((20, 20)) == (255, 0, 0)


def test_highlight_only_changes_mask_area() -> None:
    original = Image.new("RGB", (40, 40), (0, 0, 255))
    result = highlight(original, make_mask(), alpha=0.45)
    assert result.getpixel((2, 2)) == (0, 0, 255)
    red, _green, blue = result.getpixel((20, 20))
    assert red > 100
    assert blue < 200


def test_prepare_image_limits_long_edge() -> None:
    image = Image.new("RGB", (4000, 2000), (10, 20, 30))
    prepared = prepare_image(image, max_edge=1000)
    assert max(prepared.size) == 1000


def test_data_url_prefix() -> None:
    url = to_data_url(Image.new("RGB", (8, 8), (255, 255, 255)))
    assert url.startswith("data:image/png;base64,")
    assert len(url) > 40


def test_history_roundtrip(tmp_path) -> None:
    original = Image.new("RGB", (24, 24), (0, 255, 0))
    history = SessionHistory(tmp_path, original)
    version = history.add_version(
        [Image.new("RGB", (24, 24), (255, 0, 0))],
        prompt="测试",
        cost=0.3,
    )
    assert history.current is not None
    assert history.current.id == version.id
    assert history.total_cost == 0.3
    assert (history.session_dir / version.files[0]).exists()
    assert (history.session_dir / "history.json").exists()

    history.select(version.id, 0)
    loaded = history.current_image()
    assert loaded.size == (24, 24)
    assert loaded.getpixel((0, 0)) == (255, 0, 0)


def test_compose_background_color() -> None:
    foreground = Image.new("RGBA", (10, 10), (255, 0, 0, 0))
    result = compose_background(foreground, (255, 255, 255))
    assert result.getpixel((5, 5)) == (255, 255, 255)


def test_side_by_side_size() -> None:
    left = Image.new("RGB", (30, 20), (0, 0, 0))
    right = Image.new("RGB", (20, 30), (255, 255, 255))
    combined = side_by_side(left, right, gap=10)
    assert combined.width == 30 + 10 + 20
    assert combined.height == 30


def test_hex_to_rgb() -> None:
    assert hex_to_rgb("#ff0000") == (255, 0, 0)
    assert hex_to_rgb("0f0") == (0, 255, 0)


def test_siliconflow_parse_b64() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (12, 8), (10, 20, 30)).save(buffer, "PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    provider = SiliconFlowProvider(AppConfig(api_key="test"))
    image, seed = provider._parse(
        {"images": [{"b64_json": encoded}], "seed": 123}
    )
    assert image.size == (12, 8)
    assert image.getpixel((0, 0)) == (10, 20, 30)
    assert seed == 123


def test_rewriter_disabled_without_key() -> None:
    rewriter = PromptRewriter(AppConfig(zhipu_api_key=""))
    assert not rewriter.enabled
    assert rewriter.rewrite("把背景换成海边") == "把背景换成海边"
