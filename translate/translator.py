import os
import time

os.environ.setdefault('ARGOS_CHUNK_TYPE', 'MINISBD')
os.environ.setdefault('ARGOS_BEAM_SIZE', '1')
os.environ.setdefault('ARGOS_INTRA_THREADS', str(min(8, os.cpu_count() or 4)))

GOOGLE_CODES = {
    '中文': 'zh-CN',
    '英文': 'en',
    '日文': 'ja',
    '韩文': 'ko',
    '法文': 'fr',
    '德文': 'de',
    '西班牙文': 'es',
    '俄文': 'ru',
    '意大利文': 'it',
    '葡萄牙文': 'pt',
}

ARGOS_CODES = {
    '中文': 'zh',
    '英文': 'en',
    '日文': 'ja',
    '韩文': 'ko',
    '法文': 'fr',
    '德文': 'de',
    '西班牙文': 'es',
    '俄文': 'ru',
    '意大利文': 'it',
    '葡萄牙文': 'pt',
}

LANGUAGES = list(GOOGLE_CODES.keys())


class TranslationError(Exception):
    pass


class GoogleTranslatorWrapper:
    engine = 'online'

    def __init__(self, src_code, tgt_code):
        try:
            from deep_translator import GoogleTranslator
        except ImportError:
            raise TranslationError('在线翻译需要安装 deep-translator')
        self._t = GoogleTranslator(source=src_code or 'auto', target=tgt_code)

    def translate(self, text):
        last = None
        for attempt in range(3):
            try:
                out = self._t.translate(text)
                if out:
                    return out
                last = '无响应'
            except Exception as e:
                last = e
            time.sleep(1.5 + attempt)
        raise TranslationError(f'在线翻译失败: {last}')


class ArgosTranslator:
    engine = 'offline'

    def __init__(self, src_code, tgt_code):
        try:
            from argostranslate import translate
        except ImportError:
            raise TranslationError('离线翻译需要安装 argostranslate')
        self._t = translate.get_translation_from_codes(src_code, tgt_code)
        if self._t is None:
            raise TranslationError(f'未安装 {src_code}→{tgt_code} 离线模型，请先下载')

    def translate(self, text):
        try:
            out = self._t.translate(text)
            return out or ''
        except Exception as e:
            raise TranslationError(f'离线翻译失败: {e}')


def make_translator(engine, src_code, tgt_code):
    if engine == 'offline':
        return ArgosTranslator(src_code, tgt_code)
    return GoogleTranslatorWrapper(src_code, tgt_code)


def translate_lines(lines, translator, on_progress=None, cancel_event=None):
    total = len(lines)
    results = []
    i = 0
    while i < total:
        if cancel_event and cancel_event.is_set():
            raise TranslationError('翻译已取消')
        line = lines[i]
        if not line.strip():
            results.append('')
            i += 1
            _report(on_progress, i, total)
            continue
        chunk = [line]
        size = len(line)
        j = i + 1
        while j < total and lines[j].strip() and size + len(lines[j]) <= 1500:
            chunk.append(lines[j])
            size += len(lines[j])
            j += 1
        if len(chunk) == 1 and len(chunk[0]) > 1500:
            segs = [chunk[0][k:k + 1500] for k in range(0, len(chunk[0]), 1500)]
            parts = [translator.translate(seg) or '' for seg in segs]
            results.append(' '.join(p.strip() for p in parts))
        else:
            text = '\n'.join(chunk)
            out = translator.translate(text)
            parts = out.split('\n') if out else []
            if len(parts) == len(chunk):
                results.extend(parts)
            else:
                for cl in chunk:
                    results.append(translator.translate(cl) or '')
        i = j
        _report(on_progress, i, total)
    return results


def _report(on_progress, done, total):
    if on_progress:
        try:
            on_progress(done, total)
        except Exception:
            pass


def argos_installed_pairs():
    try:
        from argostranslate import translate
        out = []
        for lang in translate.get_installed_languages():
            f = getattr(lang, 'code', None) or '?'
            for tr in getattr(lang, 'translations_from', []):
                tl = getattr(tr, 'to_lang', None)
                t = getattr(tl, 'code', None) or '?'
                out.append(f'{f}→{t}')
        return out
    except Exception:
        return None


def argos_has_engine():
    try:
        from argostranslate import translate  # noqa: F401
        return True
    except Exception:
        return False


def _obtain_model_path(pkg, on_progress):
    import requests
    from argostranslate import settings
    fname = f'{pkg.type}-{pkg.code}.argosmodel'
    dest = settings.downloads_dir / fname
    if dest.exists():
        return str(dest)
    settings.downloads_dir.mkdir(parents=True, exist_ok=True)
    last_err = None
    for url in pkg.links:
        try:
            resp = requests.get(url, stream=True, timeout=(10, 180))
            resp.raise_for_status()
        except requests.RequestException as e:
            last_err = e
            continue
        total = int(resp.headers.get('Content-Length') or 0)
        done = 0
        tmp = str(dest) + '.part'
        try:
            with open(tmp, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=262144):
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        if on_progress:
                            try:
                                on_progress(done, total)
                            except Exception:
                                pass
            os.replace(tmp, str(dest))
            return str(dest)
        except requests.RequestException as e:
            last_err = e
            try:
                os.remove(tmp)
            except OSError:
                pass
    raise TranslationError(f'网络错误，无法下载模型，请检查网络或代理: {last_err}')


def download_argos_model(from_code, to_code, on_progress=None):
    try:
        from argostranslate import package
    except ImportError:
        raise TranslationError('离线翻译需要安装 argostranslate')
    try:
        from argostranslate import translate
        if translate.get_translation_from_codes(from_code, to_code) is not None:
            return 'already'
    except Exception:
        pass
    index_ok = True
    try:
        package.update_package_index()
    except Exception:
        index_ok = False
    pkgs = [p for p in package.get_available_packages()
            if p.from_code == from_code and p.to_code == to_code]
    if not pkgs:
        if not index_ok:
            raise TranslationError(
                f'无法获取 {from_code}→{to_code} 模型列表：网络不可用，'
                '请检查网络或代理后重试')
        raise TranslationError(f'没有可用的 {from_code}→{to_code} 离线模型')
    pkg = pkgs[0]
    try:
        path = _obtain_model_path(pkg, on_progress)
        package.install_from_path(path)
    except TranslationError:
        raise
    except Exception as e:
        raise TranslationError(f'模型下载/安装失败: {e}')
    try:
        from argostranslate import translate
        if translate.get_translation_from_codes(from_code, to_code) is None:
            raise TranslationError('模型已下载但安装校验未通过，请重启程序后重试')
    except TranslationError:
        raise
    except Exception as e:
        raise TranslationError(f'模型安装校验出错: {e}')
    return 'downloaded'
