import re
from difflib import SequenceMatcher

try:
    import jieba
    _HAS_JIEBA = True
except Exception:
    _HAS_JIEBA = False

_NONWORD = re.compile(r'[^\w\u4e00-\u9fff]', re.UNICODE)
_KEEP = re.compile(r'[\w\u4e00-\u9fff]', re.UNICODE)


def _normalize(w):
    return _NONWORD.sub('', w.lower())


def tokenize(text):
    tokens = []
    if not text:
        return tokens
    if _HAS_JIEBA:
        for word, start, end in jieba.tokenize(text, mode='default', HMM=False):
            if _KEEP.search(word):
                tokens.append((start, end, word))
    else:
        pattern = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*|[\u4e00-\u9fff]")
        for m in pattern.finditer(text):
            tokens.append((m.start(), m.end(), m.group()))
    return tokens


def token_at(tokens, col):
    best = None
    for i, (s, e, w) in enumerate(tokens):
        if s <= col < e:
            return i
        if col >= s:
            best = i
    return best


def warmup():
    if _HAS_JIEBA:
        try:
            jieba.initialize()
        except Exception:
            pass


def _sim(a, b):
    na = _normalize(a)
    nb = _normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def align(src_tokens, tgt_tokens):
    """单调对齐：按位置比例映射，并在小窗口内用相似度微调。

    适用于中英/英中等跨语系对照，悬停高亮表现稳定。
    """
    n = len(src_tokens)
    m = len(tgt_tokens)
    src_to_tgt = {i: [] for i in range(n)}
    tgt_to_src = {j: [] for j in range(m)}
    if n == 0 or m == 0:
        return src_to_tgt, tgt_to_src

    for i in range(n):
        j0 = int(round((i + 0.5) * m / n))
        j0 = max(0, min(m - 1, j0))
        best_j = j0
        best_s = _sim(src_tokens[i][2], tgt_tokens[j0][2])
        lo = max(0, j0 - 2)
        hi = min(m, j0 + 3)
        for j in range(lo, hi):
            s = _sim(src_tokens[i][2], tgt_tokens[j][2])
            if s > best_s:
                best_s = s
                best_j = j
        src_to_tgt[i].append(best_j)
        tgt_to_src[best_j].append(i)

    return src_to_tgt, tgt_to_src


class AlignPair:
    def __init__(self, src, tgt):
        self.src = src
        self.tgt = tgt
        self.src_tokens = tokenize(src)
        self.tgt_tokens = tokenize(tgt)
        self.src_to_tgt, self.tgt_to_src = align(self.src_tokens, self.tgt_tokens)
