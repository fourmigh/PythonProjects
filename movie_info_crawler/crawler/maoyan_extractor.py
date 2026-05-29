import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from .browser_fetcher import BrowserFetcher
from .models import MovieInfo, MovieField, SearchResult, Source
from .config_manager import ConfigManager
from .stonefont import StonefontDecoder


class MaoyanExtractor:
    SEARCH_URL = "https://m.maoyan.com/searchlist/movies"
    DETAIL_URL = "https://www.maoyan.com/films/{}"

    def __init__(self, config: ConfigManager, browser: BrowserFetcher):
        self.config = config
        self.browser = browser
        self._cached_info: Dict[str, MovieInfo] = {}

    def search(self, movie_name: str) -> List[SearchResult]:
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
            return []

        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('.movie.cell')
        if not items:
            print(f"  未找到相关电影")
            return []

        results = []
        for item in items:
            movie_id = item.get('data-id')
            if not movie_id:
                continue

            title_el = item.select_one('.name .title')
            title = title_el.get_text(strip=True) if title_el else ''

            year = ''
            date_el = item.select_one('.release')
            if date_el:
                date_text = date_el.get_text(strip=True)
                year_match = re.search(r'(\d{4})', date_text)
                if year_match:
                    year = year_match.group(1)

            url = self.DETAIL_URL.format(movie_id)

            info = MovieInfo()
            if title:
                info.set(MovieField.TITLE, title, Source.MAOYAN)
            score_el = item.select_one('.score .num')
            if score_el:
                info.set(MovieField.RATING, score_el.get_text(strip=True), Source.MAOYAN)
            cat_el = item.select_one('.catogary')
            if cat_el:
                info.set(MovieField.GENRE, cat_el.get_text(strip=True), Source.MAOYAN)
            if date_el:
                info.set(MovieField.RELEASE_DATE, date_el.get_text(strip=True), Source.MAOYAN)
            ename_el = item.select_one('.ename')
            if ename_el:
                text = ename_el.get_text(strip=True)
                if text:
                    info.set(MovieField.AKA, text, Source.MAOYAN)

            self._cached_info[url] = info
            results.append(SearchResult(title=title, url=url, year=year))

        return results

    @staticmethod
    def _extract_movie_id(url: str) -> Optional[str]:
        m = re.search(r'/films/(\d+)', url)
        return m.group(1) if m else None

    def _fetch_box_office_from_api(self, movie_id: str) -> Optional[str]:
        today = datetime.now().strftime('%Y-%m-%d')
        api_url = f'https://box.maoyan.com/promovie/api/box/second.json?beginDate={today}'
        try:
            resp = requests.get(api_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
                'Referer': 'https://piaofang.maoyan.com/',
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get('data', {}).get('list', []):
                if str(item.get('movieId')) == movie_id:
                    return item.get('sumBoxInfo', '') or None
        except Exception:
            pass
        return None

    def extract(self, url: str) -> Optional[MovieInfo]:
        print(f"  猫眼提取: GET {url}")
        info = self._cached_info.get(url, MovieInfo())

        movie_id = self._extract_movie_id(url)
        if movie_id:
            api_box_office = self._fetch_box_office_from_api(movie_id)
            if api_box_office:
                print(f"  [API] 提取到票房: {api_box_office}")
                info.set(MovieField.BOX_OFFICE, api_box_office, Source.MAOYAN)
                return info

        try:
            html = self.browser.get_html(url, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"  猫眼提取超时: [{type(e).__name__}] {e}，使用当前页面内容...")
            html = self.browser.page.content()

        html_vals = self._find_in_html(html)
        if html_vals.get('box_office') or html_vals.get('want_to_see'):
            box_office_val = html_vals.get('box_office', '')
            want_to_see_val = html_vals.get('want_to_see', '')
        else:
            page_vals = self._try_extract_inline_data()
            box_office_val = page_vals.get('box_office', '')
            want_to_see_val = page_vals.get('want_to_see', '')

        rating_count_val = ''
        if not box_office_val and not want_to_see_val:
            box_office_val, want_to_see_val, rating_count_val = self._try_stonefont_decode(html)

        if box_office_val:
            print(f"  提取到票房: {box_office_val}")
        info.set(MovieField.BOX_OFFICE, box_office_val, Source.MAOYAN)

        if want_to_see_val:
            print(f"  提取到想看人数: {want_to_see_val}")
        info.set(MovieField.WANT_TO_SEE, want_to_see_val, Source.MAOYAN)

        if rating_count_val:
            print(f"  提取到评分人数: {rating_count_val}")
        info.set(MovieField.RATING_COUNT, rating_count_val, Source.MAOYAN)

        has_extra = bool(info.get(MovieField.BOX_OFFICE, Source.MAOYAN)) or bool(
            info.get(MovieField.WANT_TO_SEE, Source.MAOYAN)) or bool(
                info.get(MovieField.RATING_COUNT, Source.MAOYAN))
        if has_extra:
            print(f"  成功提取猫眼详情数据")
        else:
            print(f"  无猫眼详情数据")

        return info

    @staticmethod
    def _find_in_html(html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        result = {'box_office': '', 'want_to_see': ''}

        for script in soup.find_all('script'):
            text = script.string or ''

            if not result['box_office']:
                for key in ['sumBoxInfo', 'boxOffice', 'boxOfficeDesc']:
                    m = re.search(r'"' + key + r'"\s*:\s*"([^"]*)"', text)
                    if m:
                        result['box_office'] = m.group(1)
                        break

            if not result['want_to_see']:
                for key in ['wantToSee', 'wishCount', 'showCount', 'show_count']:
                    m = re.search(r'"' + key + r'"\s*:\s*(\d+)', text)
                    if m:
                        result['want_to_see'] = m.group(1)
                        break

            if result['box_office'] and result['want_to_see']:
                break

        return result

    def _try_extract_inline_data(self) -> dict:
        result = self.browser.page.evaluate(r'''() => {
            for (const key of ['__INITIAL_STATE__', '__NUXT__', '__NEXT_DATA__']) {
                if (window[key]) {
                    const t = JSON.stringify(window[key]);
                    const box = (t.match(/"sumBoxInfo"\s*:\s*"([^"]*)"/) || [])[1] || '';
                    const want = (t.match(/"wantToSee"\s*:\s*(\d+)/) || [])[1] || '';
                    return {box_office: box, want_to_see: want};
                }
            }
            return null;
        }''')
        return result or {}

    def _try_stonefont_decode(self, html: str, font_data: Optional[bytes] = None) -> tuple:
        print(f"  尝试 StonefontDecoder 解码...")
        try:
            decoder = StonefontDecoder()
            mapping = decoder.build_mapping(self.browser.page, html,
                                            font_data_override=font_data)
            if not mapping:
                return ('', '', '')

            decoded_html = decoder.decode_page(self.browser.page.content())
            for span in BeautifulSoup(decoded_html, 'html.parser').select('span.stonefont'):
                print(f"  [stonefont] 解码后 stonefont 文本: {repr(span.get_text(strip=True))}")
            decoded_soup = BeautifulSoup(decoded_html, 'html.parser')

            box_office_val = self._extract_box_office(decoded_soup)
            want_to_see_val = ''
            rating_count_val = ''

            for span in decoded_soup.select('span.stonefont'):
                text = span.get_text(strip=True)
                if not re.search(r'\d', text):
                    continue
                parent_text = span.parent.get_text(strip=True) if span.parent else ''

                if '万' in parent_text or '亿' in parent_text:
                    continue
                if '评' in parent_text and '.' not in text:
                    rating_count_val = text if not rating_count_val else rating_count_val
                elif '想看' in parent_text and '.' not in text:
                    want_to_see_val = text

            exclude = frozenset()
            if box_office_val:
                clean = re.sub(r'\s*万\s*|\s*亿\s*', '', box_office_val)
                exclude = frozenset([clean, box_office_val])
            if rating_count_val:
                exclude = frozenset(list(exclude) + [rating_count_val])

            if not want_to_see_val:
                want_to_see_val = self._extract_want_to_see(decoded_soup, exclude) or ''

            if box_office_val or want_to_see_val or rating_count_val:
                print(f"  [stonefont] 解码成功: 票房='{box_office_val}', 想看='{want_to_see_val}', 评分人数='{rating_count_val}'")
            else:
                print(f"  [stonefont] 解码后未匹配到数值")

            return (box_office_val, want_to_see_val, rating_count_val)
        except Exception as e:
            print(f"  [stonefont] 解码失败: [{type(e).__name__}] {e}")
            return ('', '', '')

    def _extract_box_office(self, soup: BeautifulSoup) -> str:
        box_selectors = [
            '.stonefont-container .box-row .stonefont',
            '.movie-box .box-row',
            '.box-row span',
            '.box-item .stonefont',
            '.movie-right-info .stonefont',
            'span.stonefont',
        ]

        for sel in box_selectors:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if text and re.search(r'\d', text):
                    parent_text = el.parent.get_text(strip=True) if el.parent else text
                    match = re.search(r'([\d,]+\.?\d*\s*(?:亿|万))', parent_text)
                    if match:
                        return match.group(1)

        for sel in box_selectors:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if text and re.search(r'\d', text) and '.' not in text:
                    return text

        match = re.search(r'(\d[\d,]*\s*(?:万|亿))', ' '.join(soup.stripped_strings))
        if match:
            return match.group(1)

        return ''

    def _extract_want_to_see(self, soup: BeautifulSoup,
                             exclude_values: frozenset = frozenset()) -> str:
        want_selectors = [
            '.want-see-num .stonefont',
            '.want-num .stonefont',
            '.wish-num .stonefont',
            '.want-see .stonefont',
        ]

        for sel in want_selectors:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if text and text not in exclude_values and re.search(r'\d', text) and '.' not in text:
                    parent_text = el.parent.get_text(strip=True) if el.parent else ''
                    if '.' not in parent_text:
                        return text

        for el in soup.select('span.stonefont'):
            text = el.get_text(strip=True)
            if text and text not in exclude_values and re.search(r'\d', text) and '.' not in text:
                parent_text = el.parent.get_text(strip=True) if el.parent else ''
                if '.' not in parent_text and '评' not in parent_text:
                    return text

        return ''
