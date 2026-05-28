import re
from typing import Dict


class StonefontDecoder:
    def __init__(self):
        self._mapping: Dict[str, str] = {}

    def build_mapping(self, page) -> Dict[str, str]:
        mapping = page.evaluate('''async () => {
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
                console.log('stonefont: U+' + ch.charCodeAt(0).toString(16).toUpperCase() + ' -> ' + bestDigit + ' (diff=' + bestScore + ')');
                result[ch] = String(bestDigit);
            }
            return result;
        }''')

        if not mapping:
            return {}

        self._mapping = mapping
        for ch, d in self._mapping.items():
            print(f"    U+{ord(ch):04X} -> {d}")

        dupes = [v for v in mapping.values() if list(mapping.values()).count(v) > 1]
        if dupes:
            print(f"  [警告] 映射有重复数字: {set(dupes)}")

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
