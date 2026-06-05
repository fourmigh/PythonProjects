import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from .browser_fetcher import BrowserFetcher
from .models import MovieInfo, MovieField, SearchResult, Source
from .config_manager import ConfigManager

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
        page_vals = {} if html_vals.get('box_office') or html_vals.get('want_to_see') else self._try_extract_inline_data()

        box_office_val = html_vals.get('box_office', '') or page_vals.get('box_office', '')
        want_to_see_val = html_vals.get('want_to_see', '') or page_vals.get('want_to_see', '')
        rating_count_val = html_vals.get('rating_count', '') or page_vals.get('rating_count', '')

        if not box_office_val or not rating_count_val:
            import tempfile, os
            print("  猫眼页面含 stonefont 编码数据，正在截图供您查看...")
            self.browser.page.evaluate('document.fonts.ready')
            self.browser.page.wait_for_timeout(500)
            movie_label = re.sub(r'[\\/:*?"<>|]', '', info.get(MovieField.TITLE, Source.MAOYAN) or 'unknown')
            ss_path = os.path.join(tempfile.gettempdir(), f'maoyan_{movie_label}.png')
            self.browser.page.screenshot(path=ss_path)
            import subprocess
            subprocess.Popen(['display', '-immutable', ss_path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not box_office_val:
                box_office_val = MaoyanExtractor._ask_value("票房 (如 2534w 或 2.61y)")
            if not rating_count_val:
                rating_count_val = MaoyanExtractor._ask_value("评分人数 (如 1469)")

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
    def _ask_value(prompt: str) -> str:
        return input(f"  {prompt}: ").strip().replace('w', '万').replace('y', '亿')

    @staticmethod
    def _find_in_html(html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        result: dict = {'box_office': '', 'want_to_see': '', 'rating_count': ''}
        rating_count_keys = ['ratingCount', 'commentCount', 'scoreCount', 'evaluationCount', 'scoreNum']

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

            if not result['rating_count']:
                for key in rating_count_keys:
                    m = re.search(r'"' + key + r'"\s*:\s*(\d+)', text)
                    if m:
                        result['rating_count'] = m.group(1)
                        break

            # Debug: dump unmatched rating/score/comment/wish keys
            for m in re.finditer(
                r'"(rating|score|comment|evaluation|wish|want|box|sum|show)[^"]*"\s*:\s*(\d+|"[^"]*")',
                text, re.I
            ):
                key = m.group(1).lower()
                val = m.group(2).strip('"')
                if 'box' in key and result['box_office']:
                    continue
                if 'want' in key and result['want_to_see']:
                    continue
                if 'rating' in key or 'score' in key or 'comment' in key:
                    if result['rating_count']:
                        continue
                print(f"  [debug] script key: {m.group(1)} = {val}")

        return result

    def _try_extract_inline_data(self) -> dict:
        result = self.browser.page.evaluate(r'''() => {
            for (const key of ['__INITIAL_STATE__', '__NUXT__', '__NEXT_DATA__']) {
                if (window[key]) {
                    const t = JSON.stringify(window[key]);
                    const box = (t.match(/"sumBoxInfo"\s*:\s*"([^"]*)"/) || [])[1] || '';
                    const want = (t.match(/"wantToSee"\s*:\s*(\d+)/) || [])[1] || '';
                    const rc = (t.match(/"ratingCount"\s*:\s*(\d+)/) || [])[1] || '';
                    const cc = (t.match(/"commentCount"\s*:\s*(\d+)/) || [])[1] || '';
                    const sc = (t.match(/"scoreCount"\s*:\s*(\d+)/) || [])[1] || '';
                    return {box_office: box, want_to_see: want, rating_count: rc || cc || sc};
                }
            }
            return null;
        }''')
        return result or {}


