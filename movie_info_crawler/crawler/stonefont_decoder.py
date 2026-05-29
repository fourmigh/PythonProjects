import json
import math
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import requests
from bs4 import BeautifulSoup
from fontTools.ttLib import TTFont


class _OutlinePen:
    """fontTools Pen that samples TrueType quadratic bezier outlines."""

    def __init__(self, samples: int = 10):
        self.points: List[Tuple[float, float]] = []
        self._samples = samples
        self._start: Optional[Tuple[float, float]] = None
        self._current: Optional[Tuple[float, float]] = None

    def _add_quadratic(self, start: Tuple[float, float],
                       control: Tuple[float, float],
                       end: Tuple[float, float]) -> None:
        for i in range(1, self._samples + 1):
            t = i / self._samples
            x = (1 - t) ** 2 * start[0] + 2 * t * (1 - t) * control[0] + t * t * end[0]
            y = (1 - t) ** 2 * start[1] + 2 * t * (1 - t) * control[1] + t * t * end[1]
            self.points.append((x, y))

    def moveTo(self, pt: Tuple[float, float]) -> None:
        self._start = pt
        self._current = pt
        self.points.append(pt)

    def lineTo(self, pt: Tuple[float, float]) -> None:
        self.points.append(pt)
        self._current = pt

    def qCurveTo(self, *pts: Tuple[float, float]) -> None:
        start = self._current
        controls = list(pts)

        if len(controls) == 2:
            self._add_quadratic(start, controls[0], controls[1])
            self._current = controls[1]
        else:
            for i in range(len(controls) - 1):
                cp = controls[i]
                if i == len(controls) - 2:
                    end_pt = controls[i + 1]
                else:
                    next_cp = controls[i + 1]
                    end_pt = ((cp[0] + next_cp[0]) / 2.0,
                              (cp[1] + next_cp[1]) / 2.0)
                self._add_quadratic(start, cp, end_pt)
                start = end_pt
            self._current = controls[-1]

    def curveTo(self, *pts: Tuple[float, float]) -> None:
        for pt in pts:
            self.points.append(pt)
        self._current = pts[-1]

    def closePath(self) -> None:
        if (self._start and self._current
                and self._start != self._current):
            self.points.append(self._start)
        self._current = self._start

    def endPath(self) -> None:
        self._current = self._start


class StonefontDecoder:
    REFERENCE_FILE = 'stonefont_reference.json'

    def __init__(self, reference_dir: str = '.'):
        self._mapping: Dict[str, str] = {}
        self._reference_path = Path(reference_dir) / self.REFERENCE_FILE
        self._reference: Dict[str, List[Tuple[float, float]]] = {}

    # ── 外部接口 ──────────────────────────────────────

    def build_mapping(self, page, initial_html: Optional[str] = None,
                      font_data_override: Optional[bytes] = None) -> Dict[str, str]:
        self._mapping = {}

        if font_data_override:
            woff_data = font_data_override
        else:
            woff_data = self._try_get_font_data(page, initial_html)

        if not woff_data:
            print("  [stonefont] 未找到 woff 字体 URL，尝试 Canvas 自举...")
            pixel_mapping = self._canvas_bootstrap(page)
            if pixel_mapping:
                self._mapping = pixel_mapping
                print(f"  [stonefont] Canvas 自举映射: {len(pixel_mapping)} 个字符")
            return self._mapping

        font = TTFont(BytesIO(woff_data))
        cmap = font.getBestCmap()

        live_html = page.content()
        stonefont_chars = self._extract_stonefont_chars(live_html)
        if not stonefont_chars:
            print("  [stonefont] 页面中无 stonefont 字符")
            return {}

        # Try fontTools contour matching first (fixes 5/6 misidentification)
        digit_ref = StonefontDecoder._get_digit_reference()
        if digit_ref:
            print("  [stonefont] fontTools 轮廓匹配中...")
            for ch in stonefont_chars:
                code_point = ord(ch)
                glyph_name = cmap.get(code_point)
                if glyph_name is None:
                    continue
                points = StonefontDecoder._get_glyph_contour_points(font, glyph_name)
                if not points:
                    continue
                digit = self._match_against_reference(points, digit_ref, threshold=1.0)
                if digit is not None:
                    self._mapping[ch] = digit

            if self._mapping:
                for ch, d in self._mapping.items():
                    print(f"    U+{ord(ch):04X} -> {d}")
                print(f"  [stonefont] fontTools 匹配了 {len(self._mapping)}/{len(stonefont_chars)} 个字符")
                if len(self._mapping) >= len(stonefont_chars):
                    print("  [stonefont] 完成映射")
                    return self._mapping
                print("  [stonefont] fontTools 未完全匹配，回退到 Canvas 自举补充...")

        print("  [stonefont] 注入字体后 Canvas 自举...")
        StonefontDecoder._inject_font_to_page(page, woff_data)
        self._mapping = self._canvas_bootstrap(page) or {}

        if self._mapping:
            for ch, d in self._mapping.items():
                print(f"    U+{ord(ch):04X} -> {d}")
        else:
            print("  [stonefont] Canvas 自举未匹配到字符")

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
    def _get_woff_url(page, html: Optional[str] = None) -> Optional[str]:
        url = StonefontDecoder._get_woff_url_from_performance(page)
        if url:
            print(f"  [stonefont] Performance API 发现字体 URL: {url}")
            return url

        url = StonefontDecoder._get_woff_url_from_cssom(page)
        if url:
            print(f"  [stonefont] CSSOM 发现字体 URL: {url}")
            return url

        if html:
            url = StonefontDecoder._get_woff_url_from_html(html)
            if url:
                print(f"  [stonefont] 外部 CSS 提取到 woff URL: {url}")
                return url

        print("  [stonefont] CSSOM 和 HTML 均未找到 woff URL")
        return None

    @staticmethod
    def _get_woff_url_from_performance(page) -> Optional[str]:
        return page.evaluate('''() => {
            const entries = performance.getEntriesByType('resource');
            for (const entry of entries) {
                if (entry.initiatorType === 'css' &&
                    (entry.name.includes('.woff') || entry.name.includes('.woff2'))) {
                    return entry.name;
                }
            }
            for (const entry of entries) {
                if (entry.name.includes('.woff') || entry.name.includes('.woff2')) {
                    return entry.name;
                }
            }
            return null;
        }''')

    @staticmethod
    def _get_woff_url_from_cssom(page) -> Optional[str]:
        result = page.evaluate('''() => {
            const sheets = document.styleSheets;
            let found = null;
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
                                if (m) found = m[1];
                            }
                        }
                    }
                } catch(e) {}
            }
            return found;
        }''')

        if not result:
            return None

        url = str(result).strip()
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://maoyan.com' + url
        elif url.startswith('data:'):
            return url

        if url.startswith('http') and not re.search(r'\.eot[\?#]', url, re.I):
            return url
        return None

    @staticmethod
    def _get_woff_url_from_html(html: str) -> Optional[str]:
        soup = BeautifulSoup(html, 'html.parser')

        for link in soup.select('link[rel="stylesheet"]'):
            href = link.get('href')
            if not href:
                continue
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://maoyan.com' + href
            elif not href.startswith('http'):
                continue

            css_url = StonefontDecoder._find_woff_in_css_url(href)
            if css_url:
                return css_url

        for style in soup.select('style'):
            css_text = style.string or ''
            url = StonefontDecoder._find_woff_in_css_text(css_text)
            if url:
                return url

        return None

    @staticmethod
    def _find_woff_in_css_url(css_url: str) -> Optional[str]:
        try:
            resp = requests.get(css_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/120.0.0.0 Safari/537.36',
            }, timeout=10)
            resp.raise_for_status()
            return StonefontDecoder._find_woff_in_css_text(resp.text)
        except Exception:
            return None

    @staticmethod
    def _find_woff_in_css_text(css: str) -> Optional[str]:
        pattern = (
            r'@font-face\s*\{[^}]*?'
            r'font-family\s*:\s*["\']?(?:mtsi-font|stonefont)["\']?[^}]*?'
            r'src\s*:\s*(?:[^;]*?url\(["\']?)([^"\'\)]+\.woff2?[^"\'\)]*)'
        )
        matches = list(re.finditer(pattern, css, re.IGNORECASE | re.DOTALL))
        if not matches:
            return None
        m = matches[-1]

        url = m.group(1).strip()
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://maoyan.com' + url
        elif url.startswith('data:'):
            return url
        return url if url.startswith('http') else None

    @staticmethod
    def _download_woff(url: str, page=None) -> Optional[bytes]:
        if url.startswith('data:'):
            return StonefontDecoder._decode_data_url(url)

        data = StonefontDecoder._download_woff_requests(url)
        if data and StonefontDecoder._is_valid_font_data(data):
            return data
        if data:
            print(f"  [stonefont] requests 返回无效字体 ({len(data)} bytes, 头部: {data[:16].hex()})")

        if page is not None:
            print("  [stonefont] requests 下载无效，尝试 Playwright API...")
            data = StonefontDecoder._download_woff_via_api(page, url)
            if data and StonefontDecoder._is_valid_font_data(data):
                return data

            print("  [stonefont] 尝试浏览器内 fetch...")
            data = StonefontDecoder._download_woff_via_page(page, url)
            if data and StonefontDecoder._is_valid_font_data(data):
                return data

            print("  [stonefont] 尝试网络拦截捕获...")
            data = StonefontDecoder._capture_font_via_intercept(page, url)
            if data and StonefontDecoder._is_valid_font_data(data):
                return data

        print("  [stonefont] 无法获取有效的字体文件")
        return None

    @staticmethod
    def _decode_data_url(data_url: str) -> Optional[bytes]:
        try:
            import base64
            if ',' not in data_url:
                return None
            return base64.b64decode(data_url.split(',', 1)[1])
        except Exception as e:
            print(f"  [stonefont] data URL 解码失败: {e}")
            return None

    @staticmethod
    def _download_woff_requests(url: str) -> Optional[bytes]:
        print(f"  [stonefont] requests 下载: {url}")
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
            print(f"  [stonefont] requests 下载失败: {e}")
            return None

    @staticmethod
    def _download_woff_via_api(page, url: str) -> Optional[bytes]:
        print(f"  [stonefont] Playwright API 下载: {url}")
        try:
            response = page.request.get(url)
            if response and response.ok:
                body = response.body()
                if body:
                    print(f"  [stonefont] Playwright API 下载成功 ({len(body)} bytes)")
                    return body
        except Exception as e:
            print(f"  [stonefont] Playwright API 下载失败: {e}")
        return None

    @staticmethod
    def _download_woff_via_page(page, url: str) -> Optional[bytes]:
        print(f"  [stonefont] 浏览器内 fetch 下载: {url}")
        try:
            b64 = page.evaluate('''async (url) => {
                try {
                    const resp = await fetch(url, {
                        credentials: 'include',
                        referrerPolicy: 'unsafe-url',
                        headers: { 'Referer': document.location.href }
                    });
                    if (!resp.ok) return null;
                    const blob = await resp.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                } catch(e) { return null; }
            }''', url)
            if b64 and ',' in b64:
                import base64
                return base64.b64decode(b64.split(',', 1)[1])
        except Exception as e:
            print(f"  [stonefont] 浏览器内下载失败: {e}")
        return None

    @staticmethod
    def _capture_font_via_intercept(page, url: str) -> Optional[bytes]:
        print(f"  [stonefont] 网络拦截捕获: {url}")
        font_data = []

        def handle_route(route):
            response = route.fetch()
            body = response.body()
            font_data.append(body)
            route.fulfill(body=body)

        page.route(url, handle_route)
        try:
            page.goto(page.url, timeout=60000, wait_until='load')
            page.wait_for_timeout(1000)
            if font_data:
                return font_data[0]
        except Exception:
            pass
        finally:
            page.unroute(url)
        return None

    @staticmethod
    def _try_get_font_data(page, html: Optional[str] = None) -> Optional[bytes]:
        perf_url = StonefontDecoder._get_woff_url_from_performance(page)
        if perf_url:
            print(f"  [stonefont] Performance API 发现 URL: {perf_url}")
            data = StonefontDecoder._download_woff_via_page(page, perf_url)
            if data and StonefontDecoder._is_valid_font_data(data):
                print(f"  [stonefont] 浏览器内下载成功 ({len(data)} bytes)")
                return data
            print(f"  [stonefont] 浏览器内下载失败，尝试 requests...")
            data = StonefontDecoder._download_woff_requests(perf_url)
            if data and StonefontDecoder._is_valid_font_data(data):
                print(f"  [stonefont] requests 下载成功 ({len(data)} bytes)")
                return data

        cssom_url = StonefontDecoder._get_woff_url_from_cssom(page)
        if cssom_url:
            print(f"  [stonefont] CSSOM 发现 URL: {cssom_url}")
            data = StonefontDecoder._download_woff(cssom_url, page)
            if data:
                return data

        if html:
            html_url = StonefontDecoder._get_woff_url_from_html(html)
            if html_url:
                print(f"  [stonefont] 外部 CSS 发现 URL: {html_url}")
                data = StonefontDecoder._download_woff(html_url, page)
                if data:
                    return data

        return None

    @staticmethod
    def _is_valid_font_data(data: bytes) -> bool:
        if len(data) < 20:
            return False
        if data[:4] in (b'wOFF', b'wOF2', b'ttcf', b'\x00\x01\x00\x00', b'OTTO'):
            return True
        return False

    # ── 字符提取 ──────────────────────────────────────

    @staticmethod
    def _extract_stonefont_chars(html: str) -> Set[str]:
        soup = BeautifulSoup(html, 'html.parser')
        chars: Set[str] = set()
        for span in soup.select('span.stonefont'):
            chars.update(ch for ch in span.get_text() if ord(ch) > 0xFF)
        return chars

    # ── 字体注入 + Canvas 自举 ─────────────────────────

    @staticmethod
    def _inject_font_to_page(page, font_data: bytes, font_family: str = 'mtsi-font') -> bool:
        import base64
        b64 = base64.b64encode(font_data).decode()
        try:
            return page.evaluate(f'''async () => {{
                const font = new FontFace('{font_family}',
                    'url(data:font/woff;base64,{b64})');
                await font.load();
                document.fonts.add(font);
                return true;
            }}''')
        except Exception as e:
            print(f"  [stonefont] 字体注入失败: {e}")
            return False

    @staticmethod
    def _canvas_bootstrap(page) -> Dict[str, str]:
        return page.evaluate('''async () => {
            const spans = document.querySelectorAll('span.stonefont');
            if (!spans.length) return {};
            const text = [...spans].map(s => s.textContent).join('');
            const chars = [...new Set([...text].filter(ch => ch > '\\u00FF'))];
            if (!chars.length) return {};

            const fontFamily = window.getComputedStyle(spans[0]).fontFamily;
            try { await document.fonts.load('64px ' + fontFamily); } catch(e) {}

            const W = 64, H = 96;
            const refCache = {};

            function countHoles(mask, W, H) {
                const N = W * H;
                const visited = new Uint8Array(N);
                const stack = [];

                for (let x = 0; x < W; x++) {
                    if (!mask[x] && !visited[x]) { visited[x] = 1; stack.push(x); }
                    const bi = (H - 1) * W + x;
                    if (!mask[bi] && !visited[bi]) { visited[bi] = 1; stack.push(bi); }
                }
                for (let y = 0; y < H; y++) {
                    if (!mask[y * W] && !visited[y * W]) { visited[y * W] = 1; stack.push(y * W); }
                    const ri = y * W + W - 1;
                    if (!mask[ri] && !visited[ri]) { visited[ri] = 1; stack.push(ri); }
                }

                while (stack.length) {
                    const i = stack.pop();
                    const cy = Math.floor(i / W), cx = i % W;
                    const dirs = [[-1, 0], [1, 0], [0, -1], [0, 1]];
                    for (const [dy, dx] of dirs) {
                        const ny = cy + dy, nx = cx + dx;
                        if (ny < 0 || ny >= H || nx < 0 || nx >= W) continue;
                        const ni = ny * W + nx;
                        if (!mask[ni] && !visited[ni]) { visited[ni] = 1; stack.push(ni); }
                    }
                }

                let holes = 0;
                for (let i = 0; i < N; i++) {
                    if (!mask[i] && !visited[i]) {
                        holes++;
                        const s = [i]; visited[i] = 1;
                        while (s.length) {
                            const ci = s.pop();
                            const cy = Math.floor(ci / W), cx = ci % W;
                            for (const [dy, dx] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
                                const ny = cy + dy, nx = cx + dx;
                                if (ny < 0 || ny >= H || nx < 0 || nx >= W) continue;
                                const ni = ny * W + nx;
                                if (!mask[ni] && !visited[ni]) { visited[ni] = 1; s.push(ni); }
                            }
                        }
                    }
                }
                return holes;
            }

            function getRefDigit(d) {
                if (refCache[d]) return refCache[d];
                const c = document.createElement('canvas');
                c.width = W; c.height = H;
                const ctx = c.getContext('2d');
                ctx.font = '64px sans-serif';
                ctx.textBaseline = 'middle';
                ctx.textAlign = 'center';
                ctx.fillText(String(d), W / 2, H / 2);
                const img = ctx.getImageData(0, 0, W, H);
                const mask = new Uint8Array(W * H);
                const hProfile = new Array(H).fill(0);
                const vProfile = new Array(W).fill(0);
                let topPixels = 0, botPixels = 0;
                const mid = Math.floor(H / 2);
                for (let y = 0; y < H; y++) {
                    for (let x = 0; x < W; x++) {
                        const i = y * W + x;
                        const val = img.data[i * 4 + 3] > 0 ? 1 : 0;
                        mask[i] = val;
                        if (val) {
                            hProfile[y]++;
                            vProfile[x]++;
                            if (y < mid) topPixels++;
                            else botPixels++;
                        }
                    }
                }
                const ratio = botPixels > 0 ? topPixels / botPixels : 0;
                const holeCount = countHoles(mask, W, H);
                refCache[d] = { mask, ratio, hProfile, vProfile, holeCount };
                return refCache[d];
            }

            const result = {};
            for (const ch of chars) {
                const c = document.createElement('canvas');
                c.width = W; c.height = H;
                const ctx = c.getContext('2d');
                ctx.font = '64px ' + fontFamily;
                ctx.textBaseline = 'middle';
                ctx.textAlign = 'center';
                ctx.fillText(ch, W / 2, H / 2);
                const img = ctx.getImageData(0, 0, W, H);

                const mask = new Uint8Array(W * H);
                const hProfile = new Array(H).fill(0);
                const vProfile = new Array(W).fill(0);
                let topPixels = 0, botPixels = 0;
                const mid = Math.floor(H / 2);
                for (let y = 0; y < H; y++) {
                    for (let x = 0; x < W; x++) {
                        const i = y * W + x;
                        const val = img.data[i * 4 + 3] > 0 ? 1 : 0;
                        mask[i] = val;
                        if (val) {
                            hProfile[y]++;
                            vProfile[x]++;
                            if (y < mid) topPixels++;
                            else botPixels++;
                        }
                    }
                }
                const maskRatio = botPixels > 0 ? topPixels / botPixels : 0;
                const glyphHoles = countHoles(mask, W, H);

                let bestDigit = -1;
                let bestScore = -Infinity;
                for (let d = 0; d <= 9; d++) {
                    const ref = getRefDigit(d);
                    let intersection = 0, union = 0;
                    for (let i = 0; i < W * H; i++) {
                        if (mask[i]) {
                            union++;
                            if (ref.mask[i]) intersection++;
                        } else if (ref.mask[i]) {
                            union++;
                        }
                    }
                    const jaccard = union > 0 ? intersection / union : 0;

                    let hSim = 0, hTotal = 0;
                    for (let y = 0; y < H; y++) {
                        hSim += Math.min(hProfile[y], ref.hProfile[y]);
                        hTotal += Math.max(hProfile[y], ref.hProfile[y]);
                    }
                    const hScore = hTotal > 0 ? hSim / hTotal : 1;

                    let vSim = 0, vTotal = 0;
                    for (let x = 0; x < W; x++) {
                        vSim += Math.min(vProfile[x], ref.vProfile[x]);
                        vTotal += Math.max(vProfile[x], ref.vProfile[x]);
                    }
                    const vScore = vTotal > 0 ? vSim / vTotal : 1;

                    const ratioPenalty = Math.abs(maskRatio - ref.ratio) * 0.1;
                    const holePenalty = (glyphHoles !== ref.holeCount) ? 0.5 : 0;
                    const score = jaccard * 0.3 + hScore * 0.2 + vScore * 0.2 - ratioPenalty - holePenalty;
                    if (score > bestScore) {
                        bestScore = score;
                        bestDigit = d;
                    }
                }
                result[ch] = String(bestDigit);
            }
            return result;
        }''')

    # ── 数字参考轮廓（系统字体） ──────────────────────

    _DIGIT_REFERENCE_CACHE: Optional[Dict[str, List[Tuple[float, float]]]] = None

    @staticmethod
    def _get_digit_reference() -> Dict[str, List[Tuple[float, float]]]:
        if StonefontDecoder._DIGIT_REFERENCE_CACHE is not None:
            return StonefontDecoder._DIGIT_REFERENCE_CACHE

        font_paths = [
            r'C:\Windows\Fonts\arial.ttf',
            r'C:\Windows\Fonts\Arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/TTF/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf',
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = TTFont(font_path)
                    cmap = font.getBestCmap()
                    reference = {}
                    for d in range(10):
                        glyph_name = cmap.get(ord(str(d)))
                        if glyph_name:
                            points = StonefontDecoder._get_glyph_contour_points(font, glyph_name)
                            if points:
                                reference[str(d)] = points
                    font.close()
                    if len(reference) >= 8:
                        print(f"  [stonefont] 从 {font_path} 加载数字参考 ({len(reference)} 个数字)")
                        StonefontDecoder._DIGIT_REFERENCE_CACHE = reference
                        return reference
                except Exception as e:
                    print(f"  [stonefont] 加载 {font_path} 失败: {e}")
                    continue

        print("  [stonefont] 未找到系统字体，跳过 fontTools 匹配")
        StonefontDecoder._DIGIT_REFERENCE_CACHE = {}
        return {}

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
        font: TTFont, glyph_name: str, samples: int = 10
    ) -> List[Tuple[float, float]]:
        glyf = font['glyf']
        glyph = glyf[glyph_name]

        if not hasattr(glyph, 'coordinates'):
            return []

        # Try _OutlinePen first (dense TrueType quadratic bezier sampling)
        pen = _OutlinePen(samples)
        try:
            glyph.draw(pen, glyf)
        except Exception as e:
            print(f"  [stonefont] _OutlinePen 失败 ({glyph_name}): {e}")

        if pen.points:
            return StonefontDecoder._normalize_points(pen.points)

        # Fallback: use all raw coordinates (on + off curve)
        coords = list(glyph.coordinates)
        if not coords:
            return []
        points = [(float(x), float(y)) for x, y in coords]
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

        def avg_min_dist(a, b):
            total = 0.0
            for p in a:
                total += min(
                    math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2)
                    for q in b
                )
            return total / len(a)

        return max(avg_min_dist(pts1, pts2), avg_min_dist(pts2, pts1))

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
