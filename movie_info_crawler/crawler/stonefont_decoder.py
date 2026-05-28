import re
from typing import Dict


class StonefontDecoder:
    def __init__(self):
        self._mapping: Dict[str, str] = {}

    def build_mapping(self, page) -> Dict[str, str]:
        features = page.evaluate('''() => {
            const spans = document.querySelectorAll('span.stonefont');
            const chars = [...new Set([...spans].map(s => s.textContent).join(''))];
            const results = {};
            for (const ch of chars) {
                const c = document.createElement('canvas');
                c.width = 100; c.height = 100;
                const ctx = c.getContext('2d');
                ctx.clearRect(0, 0, 100, 100);
                ctx.font = '72px mtsi-font';
                ctx.fillStyle = 'black';
                ctx.textBaseline = 'middle';
                ctx.textAlign = 'center';
                ctx.fillText(ch, 50, 50);
                const data = ctx.getImageData(0, 0, 100, 100).data;

                let xMin = 100, xMax = 0, yMin = 100, yMax = 0;
                let totalPixels = 0;
                for (let y = 0; y < 100; y++) {
                    for (let x = 0; x < 100; x++) {
                        if (data[(y * 100 + x) * 4 + 3] > 0) {
                            totalPixels++;
                            if (x < xMin) xMin = x;
                            if (x > xMax) xMax = x;
                            if (y < yMin) yMin = y;
                            if (y > yMax) yMax = y;
                        }
                    }
                }
                const w = xMax - xMin + 1;
                const h = yMax - yMin + 1;
                const cx = (xMin + xMax) / 2;
                const cy = (yMin + yMax) / 2;

                let leftPixels = 0, topPixels = 0, upperPixels = 0;
                for (let y = yMin; y <= yMax; y++) {
                    for (let x = xMin; x <= xMax; x++) {
                        if (data[(y * 100 + x) * 4 + 3] > 0) {
                            if (x < cx) leftPixels++;
                            if (y < cy) topPixels++;
                            if (y < cy - h * 0.2) upperPixels++;
                        }
                    }
                }

                let holeScore = 0;
                const scanY = Math.round(cy);
                if (scanY >= yMin && scanY <= yMax) {
                    let inGlyph = false;
                    let transCount = 0;
                    for (let x = xMin; x <= xMax; x++) {
                        const alpha = data[(scanY * 100 + x) * 4 + 3];
                        if (alpha > 0) {
                            if (!inGlyph) { transCount++; inGlyph = true; }
                        } else {
                            if (inGlyph) { transCount++; inGlyph = false; }
                        }
                    }
                    if (inGlyph) transCount++;
                    holeScore = Math.max(0, transCount - 2);
                }

                results[ch] = {
                    totalPixels, w, h,
                    ratio: w / h,
                    leftRatio: totalPixels > 0 ? leftPixels / totalPixels : 0,
                    topRatio: totalPixels > 0 ? topPixels / totalPixels : 0,
                    upperRatio: totalPixels > 0 ? upperPixels / totalPixels : 0,
                    holeScore,
                };
            }
            return results;
        }''')

        if not features:
            return {}

        self._mapping = self._classify(features)
        return self._mapping

    def _classify(self, features: dict) -> Dict[str, str]:
        items = [(ch, f) for ch, f in features.items()]
        mapping = {}
        remaining = {ch: f for ch, f in items}

        for ch, f in items:
            print(f"    U+{ord(ch):04X} pixels={f['totalPixels']} "
                  f"ratio={f['ratio']:.2f} left={f['leftRatio']:.2f} "
                  f"top={f['topRatio']:.2f} upper={f['upperRatio']:.2f} "
                  f"hole={f['holeScore']}")

        for ch, f in items:
            if f['ratio'] < 0.35:
                mapping[ch] = '1'
                remaining.pop(ch)
                print(f"    → 1 (ratio={f['ratio']:.2f} < 0.35)")

        if not remaining:
            return mapping

        def by_pixels(item):
            return -item[1]['totalPixels']
        sorted_by_px = sorted(remaining.items(), key=by_px)
        highest, lowest = sorted_by_px[0][0], sorted_by_px[-1][0]
        mapping[highest] = '8'
        remaining.pop(highest)
        print(f"    → 8 (pixels最高={features[highest]['totalPixels']})")

        if len(remaining) == 1:
            ch = list(remaining.keys())[0]
            mapping[ch] = '0'
            return mapping

        def by_left(item):
            return -item[1]['leftRatio']
        sorted_by_left = sorted(remaining.items(), key=by_left)
        high_left = sorted_by_left[0][0]

        def by_top(item):
            return -item[1]['topRatio']
        sorted_by_top = sorted(remaining.items(), key=by_top)
        high_top = sorted_by_top[0][0]

        low_left = sorted_by_left[-1][0]
        low_top = sorted_by_top[-1][0]

        hole_items = [(ch, f) for ch, f in remaining.items() if f['holeScore'] >= 2]

        if hole_items:
            for ch, f in hole_items:
                if ch not in remaining:
                    continue
                if f['upperRatio'] < 0.5:
                    mapping[ch] = '9'
                else:
                    mapping[ch] = '6'
                remaining.pop(ch)
                print(f"    → {mapping[ch]} (holescore={f['holeScore']}, upper={f['upperRatio']:.2f})")

        zero_candidates = [(ch, f) for ch, f in remaining.items()
                           if 0.45 <= f['ratio'] <= 0.75 and f['holeScore'] == 0]
        for ch, f in zero_candidates:
            if ch not in remaining:
                continue
            if 0.48 <= f['topRatio'] <= 0.52:
                mapping[ch] = '0'
                remaining.pop(ch)
                print(f"    → 0 (ratio={f['ratio']:.2f} top={f['topRatio']:.2f})")

        while remaining:
            ch, f = list(remaining.items())[0]
            if f['leftRatio'] > 0.6:
                mapping[ch] = '4'
                remaining.pop(ch)
                print(f"    → 4 (leftRatio={f['leftRatio']:.2f})")
            elif f['leftRatio'] < 0.4:
                mapping[ch] = '7'
                remaining.pop(ch)
                print(f"    → 7 (leftRatio={f['leftRatio']:.2f})")
            elif f['topRatio'] > 0.55:
                mapping[ch] = '5'
                remaining.pop(ch)
                print(f"    → 5 (topRatio={f['topRatio']:.2f})")
            elif f['ratio'] < 0.5:
                mapping[ch] = '3'
                remaining.pop(ch)
                print(f"    → 3 (ratio={f['ratio']:.2f})")
            else:
                mapping[ch] = '2'
                remaining.pop(ch)
                print(f"    → 2 (ratio={f['ratio']:.2f})")

        dupes = [v for v in mapping.values() if list(mapping.values()).count(v) > 1]
        if dupes:
            print(f"  [警告] 映射有重复数字: {set(dupes)}")

        return mapping

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
