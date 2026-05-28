import json
import math
import re
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import requests
from bs4 import BeautifulSoup
from fontTools.ttLib import TTFont


class StonefontDecoder:
    REFERENCE_FILE = 'stonefont_reference.json'

    def __init__(self, reference_dir: str = '.'):
        self._mapping: Dict[str, str] = {}
        self._reference_path = Path(reference_dir) / self.REFERENCE_FILE
        self._reference: Dict[str, List[Tuple[float, float]]] = {}

    # ── 外部接口 ──────────────────────────────────────

    def build_mapping(self, page, html: Optional[str] = None) -> Dict[str, str]:
        self._mapping = {}

        woff_url = self._get_woff_url(page)
        if not woff_url:
            print("  [stonefont] 未找到 woff 字体 URL")
            return {}

        woff_data = self._download_woff(woff_url)
        if not woff_data:
            return {}

        font = TTFont(BytesIO(woff_data))
        cmap = font.getBestCmap()

        if html is None:
            html = page.content()
        stonefont_chars = self._extract_stonefont_chars(html)
        if not stonefont_chars:
            print("  [stonefont] 页面中无 stonefont 字符")
            return {}

        reference = self._load_reference()
        if not reference:
            print("  [stonefont] 无参考轮廓，启动 Canvas 自举...")
            pixel_mapping = self._canvas_bootstrap(page)
            if not pixel_mapping:
                print("  [stonefont] Canvas 自举失败")
                return {}
            reference = self._build_reference_from_mapping(font, cmap, pixel_mapping)
            if not reference:
                print("  [stonefont] 无法从自举结果构建参考轮廓")
                return {}
            self._save_reference(reference)
            print(f"  [stonefont] 参考轮廓已保存 ({len(reference)} 个数字)")

        self._reference = reference
        for code in stonefont_chars:
            code_point = ord(code)
            glyph_name = cmap.get(code_point)
            if glyph_name is None:
                print(f"  [stonefont] 警告: U+{code_point:04X} 不在字体 cmap 中")
                continue
            points = self._get_glyph_contour_points(font, glyph_name)
            if not points:
                continue
            digit = self._match_against_reference(points, reference)
            if digit is not None:
                self._mapping[code] = digit

        if self._mapping:
            for ch, d in self._mapping.items():
                print(f"    U+{ord(ch):04X} -> {d}")
        else:
            print("  [stonefont] 未匹配到任何字符")

        return self._mapping

    def decode_text(self, text: str) -> str:
        result = []
        for ch in text:
            result.append(self._mapping.get(ch, ch))
        return ''.join(result)

    def decode_page(self, html: str) -> str:
        if not self._mapping:
            return html

        def replace_stonefont(match):
            inner = match.group(1)
            return f'<span class="stonefont">{self.decode_text(inner)}</span>'

        decoded = re.sub(
            r'<span[^>]*class="[^"]*stonefont[^"]*"[^>]*>(.*?)</span>',
            replace_stonefont,
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        return decoded

    # ── woff URL 提取 ─────────────────────────────────

    @staticmethod
    def _get_woff_url(page) -> Optional[str]:
        result = page.evaluate('''() => {
            const sheets = document.styleSheets;
            for (let i = 0; i < sheets.length; i++) {
                try {
                    const rules = sheets[i].cssRules || sheets[i].rules;
                    if (!rules) continue;
                    for (let j = 0; j < rules.length; j++) {
                        const rule = rules[j];
                        if (rule instanceof CSSFontFaceRule) {
                            const family = rule.style.fontFamily
                                .replace(/["']/g, '').trim();
                            if (family === 'mtsi-font' || family === 'stonefont') {
                                const src = rule.style.src || '';
                                const m = src.match(/url\\(['"]?([^'")]+)['"]?\\)/);
                                if (m) return m[1];
                            }
                        }
                    }
                } catch(e) {}
            }
            return null;
        }''')

        if not result:
            return None

        url = str(result).strip()
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://maoyan.com' + url

        return url if url.startswith('http') else None

    @staticmethod
    def _download_woff(url: str) -> Optional[bytes]:
        try:
            resp = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://maoyan.com/',
            }, timeout=15)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            print(f"  [stonefont] 下载 woff 失败: {e}")
            return None

    # ── 字符提取 ──────────────────────────────────────

    @staticmethod
    def _extract_stonefont_chars(html: str) -> Set[str]:
        soup = BeautifulSoup(html, 'html.parser')
        chars: Set[str] = set()
        for span in soup.select('span.stonefont'):
            chars.update(ch for ch in span.get_text() if ord(ch) > 0xFF)
        return chars

    # ── Canvas 自举 (复用现有像素匹配) ──────────────────

    @staticmethod
    def _canvas_bootstrap(page) -> Dict[str, str]:
        return page.evaluate('''async () => {
            const spans = document.querySelectorAll('span.stonefont');
            if (!spans.length) return {};
            const text = [...spans].map(s => s.textContent).join('');
            const chars = [...new Set([...text].filter(ch => ch > '\\u00FF'))];
            if (!chars.length) return {};

            const fontFamily = window.getComputedStyle(spans[0]).fontFamily;
            try { await document.fonts.load('40px ' + fontFamily); } catch(e) {}

            const W = 36, H = 54;
            const refCache = {};

            function getRefDigit(d) {
                if (refCache[d]) return refCache[d];
                const c = document.createElement('canvas');
                c.width = W; c.height = H;
                const ctx = c.getContext('2d');
                ctx.font = '40px sans-serif';
                ctx.textBaseline = 'middle';
                ctx.textAlign = 'center';
                ctx.fillText(String(d), W / 2, H / 2);
                const img = ctx.getImageData(0, 0, W, H);
                const mask = new Uint8Array(W * H);
                for (let i = 0; i < W * H; i++) {
                    mask[i] = img.data[i * 4 + 3] > 0 ? 1 : 0;
                }
                refCache[d] = mask;
                return mask;
            }

            const result = {};
            for (const ch of chars) {
                const c = document.createElement('canvas');
                c.width = W; c.height = H;
                const ctx = c.getContext('2d');
                ctx.font = '40px ' + fontFamily;
                ctx.textBaseline = 'middle';
                ctx.textAlign = 'center';
                ctx.fillText(ch, W / 2, H / 2);
                const img = ctx.getImageData(0, 0, W, H);

                const mask = new Uint8Array(W * H);
                for (let i = 0; i < W * H; i++) {
                    mask[i] = img.data[i * 4 + 3] > 0 ? 1 : 0;
                }

                let bestDigit = -1;
                let bestScore = Infinity;
                for (let d = 0; d <= 9; d++) {
                    const ref = getRefDigit(d);
                    let diff = 0;
                    for (let i = 0; i < W * H; i++) {
                        if (mask[i] !== ref[i]) diff++;
                    }
                    if (diff < bestScore) {
                        bestScore = diff;
                        bestDigit = d;
                    }
                }
                result[ch] = String(bestDigit);
            }
            return result;
        }''')

    # ── 参考轮廓构建 ──────────────────────────────────

    @staticmethod
    def _build_reference_from_mapping(
        font: TTFont,
        cmap: Dict,
        pixel_mapping: Dict[str, str]
    ) -> Dict[str, List[Tuple[float, float]]]:
        reference = {}
        for char_text, digit in pixel_mapping.items():
            if digit in reference:
                continue
            code_point = ord(char_text)
            glyph_name = cmap.get(code_point)
            if glyph_name is None:
                continue
            points = StonefontDecoder._get_glyph_contour_points(font, glyph_name)
            if points:
                reference[digit] = points
        return reference

    # ── 字形轮廓提取 ──────────────────────────────────

    @staticmethod
    def _get_glyph_contour_points(
        font: TTFont, glyph_name: str
    ) -> List[Tuple[float, float]]:
        glyf = font['glyf']
        glyph = glyf[glyph_name]

        if not hasattr(glyph, 'coordinates') or glyph.numberOfContours <= 0:
            return []

        points = []
        for i, (x, y) in enumerate(glyph.coordinates):
            if glyph.flags[i] & 1:
                points.append((float(x), float(y)))

        if not points:
            return []

        return StonefontDecoder._normalize_points(points)

    @staticmethod
    def _normalize_points(
        points: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        w = max(xs) - min(xs) or 1
        h = max(ys) - min(ys) or 1
        scale = max(w, h) / 2
        return [((x - cx) / scale, (y - cy) / scale) for x, y in points]

    # ── 轮廓匹配 ──────────────────────────────────────

    @staticmethod
    def _compare_contours(
        pts1: List[Tuple[float, float]],
        pts2: List[Tuple[float, float]]
    ) -> float:
        if not pts1 or not pts2:
            return float('inf')

        total = 0.0
        for p1 in pts1:
            min_dist = min(
                math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
                for p2 in pts2
            )
            total += min_dist
        return total / len(pts1)

    def _match_against_reference(
        self,
        points: List[Tuple[float, float]],
        reference: Dict[str, List[Tuple[float, float]]],
        threshold: float = 0.5
    ) -> Optional[str]:
        best_digit = None
        best_score = float('inf')

        for digit, ref_points in reference.items():
            score = self._compare_contours(points, ref_points)
            if score < best_score:
                best_score = score
                best_digit = digit

        if best_score > threshold:
            return None
        return best_digit

    # ── 参考持久化 ────────────────────────────────────

    def _load_reference(self) -> Dict[str, List[Tuple[float, float]]]:
        if not self._reference_path.exists():
            return {}
        try:
            with open(self._reference_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            ref = {}
            for digit, pts in data.get('digits', {}).items():
                ref[digit] = [(float(x), float(y)) for x, y in pts]
            return ref
        except Exception as e:
            print(f"  [stonefont] 加载参考文件失败: {e}")
            return {}

    def _save_reference(self, reference: Dict[str, List[Tuple[float, float]]]) -> None:
        data = {
            'version': 1,
            'digits': {
                digit: [[float(x), float(y)] for x, y in pts]
                for digit, pts in reference.items()
            }
        }
        try:
            with open(self._reference_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [stonefont] 保存参考文件失败: {e}")
