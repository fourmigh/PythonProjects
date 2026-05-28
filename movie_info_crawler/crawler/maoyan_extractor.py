import re
from typing import Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from .browser_fetcher import BrowserFetcher
from .models import MovieInfo, MovieField, Source
from .config_manager import ConfigManager
from .stonefont_decoder import StonefontDecoder


class MaoyanExtractor:
    SEARCH_URL = "https://m.maoyan.com/searchlist/movies"
    DETAIL_URL = "https://www.maoyan.com/films/{}"

    def __init__(self, config: ConfigManager, browser: BrowserFetcher):
        self.config = config
        self.browser = browser
        self._cached_info: Optional[MovieInfo] = None

    def search(self, movie_name: str) -> Optional[str]:
        params = {'keyword': movie_name, 'ci': 1, 'limit': 5, 'offset': 0}
        full_url = f"{self.SEARCH_URL}?{urlencode(params)}"
        print(f"  猫眼搜索: GET {full_url}")

        try:
            resp = requests.get(full_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0'
            }, timeout=15)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"  猫眼搜索失败: [{type(e).__name__}] {e}")
            return None

        soup = BeautifulSoup(html, 'html.parser')
        item = soup.select_one('.movie.cell')
        if not item:
            print(f"  未找到相关电影")
            return None

        movie_id = item.get('data-id')
        if not movie_id:
            print(f"  无法获取电影 ID")
            return None

        info = MovieInfo()
        title_el = item.select_one('.name .title')
        if title_el:
            info.set(MovieField.TITLE, title_el.get_text(strip=True), Source.MAOYAN)

        score_el = item.select_one('.score .num')
        if score_el:
            info.set(MovieField.RATING, score_el.get_text(strip=True), Source.MAOYAN)

        cat_el = item.select_one('.catogary')
        if cat_el:
            info.set(MovieField.GENRE, cat_el.get_text(strip=True), Source.MAOYAN)

        date_el = item.select_one('.release')
        if date_el:
            info.set(MovieField.RELEASE_DATE, date_el.get_text(strip=True), Source.MAOYAN)

        ename_el = item.select_one('.ename')
        if ename_el:
            text = ename_el.get_text(strip=True)
            if text:
                info.set(MovieField.AKA, text, Source.MAOYAN)

        has_data = any(
            info.get(f, Source.MAOYAN) for f in MovieField
            if f is not MovieField.TITLE
        )
        if has_data:
            self._cached_info = info

        return self.DETAIL_URL.format(movie_id)

    def extract(self, url: str) -> Optional[MovieInfo]:
        print(f"  猫眼提取: GET {url}")

        try:
            html = self.browser.get_html(url, timeout=60000, wait_until="networkidle")
        except Exception as e:
            print(f"  猫眼提取失败: [{type(e).__name__}] {e}")
            return self._cached_info

        decoder = StonefontDecoder()
        try:
            decoder.build_mapping(self.browser.page)
        except Exception as e:
            print(f"  字体映射失败: {e}")

        decoded_html = decoder.decode_page(html)
        soup = BeautifulSoup(decoded_html, 'html.parser')

        decoded_stonefont = [s.get_text(strip=True) for s in soup.select('span.stonefont') if s.get_text(strip=True)]
        if decoded_stonefont:
            print(f"  解码后 stonefont 文本: {decoded_stonefont[:5]}")

        info = self._cached_info or MovieInfo()
        box_office_val = self._extract_box_office(soup)
        if box_office_val:
            print(f"  提取到票房: {box_office_val}")
        info.set(MovieField.BOX_OFFICE, box_office_val, Source.MAOYAN)

        want_to_see_val = self._extract_want_to_see(soup)
        if want_to_see_val:
            print(f"  提取到想看人数: {want_to_see_val}")
        info.set(MovieField.WANT_TO_SEE, want_to_see_val, Source.MAOYAN)

        has_extra = bool(info.get(MovieField.BOX_OFFICE, Source.MAOYAN)) or bool(
            info.get(MovieField.WANT_TO_SEE, Source.MAOYAN))
        if has_extra:
            print(f"  成功提取猫眼详情数据")
        else:
            print(f"  无猫眼详情数据")

        return info

    def _extract_box_office(self, soup: BeautifulSoup) -> str:
        box_selectors = [
            '.stonefont-container .box-row .stonefont',
            '.movie-box .box-row',
            '.box-row span',
            '.box-item .stonefont',
            '.movie-right-info .stonefont',
            'span.stonefont',
        ]

        stonefont_texts = []
        for sel in box_selectors:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if text and re.search(r'\d', text):
                    stonefont_texts.append(text)

        for text in stonefont_texts:
            match = re.search(r'([\d,]+\.?\d*\s*(?:亿|万))', text)
            if match:
                return match.group(1)

        all_text = ' '.join(stonefont_texts)
        match = re.search(r'[\d,]+\.?\d*\s*(?:亿|万)', all_text)
        if match:
            return match.group(0)

        return ''

    def _extract_want_to_see(self, soup: BeautifulSoup) -> str:
        want_selectors = [
            '.want-see-num .stonefont',
            '.want-num .stonefont',
            '.wish-num .stonefont',
            '.want-see .stonefont',
            'span.stonefont',
        ]

        for sel in want_selectors:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if text and re.search(r'\d', text):
                    return text

        return ''
