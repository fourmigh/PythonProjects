"""搜索模块"""

import json
import re
from typing import List
from urllib.parse import urlencode

from .browser_fetcher import BrowserFetcher
from .models import SearchResult
from .config_manager import ConfigManager


class DbSearch:
    """搜索类"""

    SEARCH_URL = "https://movie.douban.com/subject_search"

    def __init__(self, config: ConfigManager, browser: BrowserFetcher):
        self.config = config
        self.browser = browser

    def search(self, movie_name: str) -> List[SearchResult]:
        """搜索电影，返回搜索结果列表"""
        params = {
            'search_text': movie_name,
            'cat': 1002,
        }
        full_url = f"{self.SEARCH_URL}?{urlencode(params)}"
        print(f"  请求: GET {full_url}")

        try:
            html = self.browser.get_html(full_url, wait_for_data=True)
        except Exception as e:
            print(f"  搜索请求失败: [{type(e).__name__}] {e}")
            return []

        return self._parse_search_results(html)

    def _parse_search_results(self, html: str) -> List[SearchResult]:
        """从页面中提取 window.__DATA__ JSON 解析搜索结果"""
        results = []
        seen_urls = set()

        match = re.search(r'window\.__DATA__\s*=\s*({.*?});', html, re.DOTALL)
        if not match:
            print(f"  无法定位搜索结果数据")
            return []

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            print(f"  解析搜索数据失败: {e}")
            return []

        error_info = data.get('error_info', '')
        if error_info:
            print(f"  服务端提示: {error_info}")

        for item in data.get('items', []):
            title = item.get('title', '').strip()
            url = item.get('url', '').strip()
            if not title or not url or '/subject/' not in url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            year = item.get('year', '')
            if not year:
                year_match = re.search(r'(\d{4})', title)
                if year_match:
                    year = year_match.group(1)

            title_clean = re.sub(r'\s*\(\d{4}\)\s*', '', title).strip() if year else title

            results.append(SearchResult(title=title_clean, url=url, year=year))

            if len(results) >= self.config.max_search_results:
                break

        if not results:
            print(f"  搜索结果为空")
            if error_info:
                print(f"  原因: {error_info}")

        return results