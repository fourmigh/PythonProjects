"""信息提取模块 - 动态支持所有字段"""

import re
from typing import Optional

from bs4 import BeautifulSoup

from .browser_fetcher import BrowserFetcher
from .models import MovieInfo, MovieField
from .config_manager import ConfigManager


class InfoExtractor:
    """电影信息提取类 - 使用真实浏览器获取页面"""

    def __init__(self, config: ConfigManager, browser: BrowserFetcher):
        self.config = config
        self.browser = browser

    def extract(self, url: str) -> Optional[MovieInfo]:
        """从豆瓣电影页面提取所有信息"""
        print(f"  请求: GET {url}")

        try:
            html = self.browser.get_html(url)
        except Exception as e:
            print(f"  提取失败: [{type(e).__name__}] {e}")
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # 检查是否为 404 等错误页
        if '你想访问的页面不存在' in html or '页面不存在' in html:
            print(f"  提取失败: 页面不存在 (404)")
            return None

        info = MovieInfo()
        info.set(MovieField.DOUBAN_LINK, url)
        self._extract_all_fields(soup, info)

        title = info.get(MovieField.TITLE)
        has_data = bool(title) and any(
            info.get(f) for f in MovieField
            if f not in (MovieField.TITLE, MovieField.DOUBAN_LINK)
        )
        if not has_data:
            print(f"  提取结果为空，完整响应:\n{html}")
            return None

        return info
    
    def _extract_all_fields(self, soup: BeautifulSoup, info: MovieInfo) -> None:
        """提取所有字段"""
        
        # 1. 提取片名和年份
        self._extract_title_and_year(soup, info)
        
        # 2. 提取评分信息
        self._extract_rating(soup, info)
        
        # 3. 提取基本信息（从info区域）
        self._extract_basic_info(soup, info)
        
        # 4. 提取简介
        self._extract_summary(soup, info)
    
    def _extract_title_and_year(self, soup: BeautifulSoup, info: MovieInfo) -> None:
        """提取片名和年份"""
        # 片名
        title_elem = soup.select_one('h1 span[property="v:itemreviewed"]')
        if title_elem:
            info.set(MovieField.TITLE, title_elem.get_text(strip=True))
        else:
            title_elem = soup.select_one('h1')
            if title_elem:
                full_title = title_elem.get_text(strip=True)
                info.set(MovieField.TITLE, full_title.split('/')[0].strip())
        
        # 年份
        year_elem = soup.select_one('h1 .year, .year')
        if year_elem:
            match = re.search(r'(\d{4})', year_elem.get_text())
            if match:
                info.set(MovieField.YEAR, match.group(1))
    
    def _extract_rating(self, soup: BeautifulSoup, info: MovieInfo) -> None:
        """提取评分信息"""
        rating_elem = soup.select_one('[property="v:average"]')
        if rating_elem:
            info.set(MovieField.RATING, rating_elem.get_text(strip=True))
        
        votes_elem = soup.select_one('[property="v:votes"]')
        if votes_elem:
            info.set(MovieField.RATING_COUNT, votes_elem.get_text(strip=True))
    
    def _extract_basic_info(self, soup: BeautifulSoup, info: MovieInfo) -> None:
        """提取基本信息"""
        info_elem = soup.select_one('#info')
        if not info_elem:
            return
        
        # 获取纯文本用于简单匹配
        info_text = info_elem.get_text(strip=True)
        
        # 定义字段映射：中文标签 -> MovieField
        field_mapping = {
            '导演': MovieField.DIRECTOR,
            '编剧': MovieField.SCREENWRITER,
            '主演': MovieField.ACTORS,
            '类型': MovieField.GENRE,
            '制片国家/地区': MovieField.REGION,
            '语言': MovieField.LANGUAGE,
            '上映日期': MovieField.RELEASE_DATE,
            '片长': MovieField.RUNTIME,
            '又名': MovieField.AKA,
            'IMDb': MovieField.IMDB_LINK
        }
        
        # 从HTML中提取结构化信息
        for label, field in field_mapping.items():
            # 尝试从info区域直接提取
            elem = info_elem.find('span', string=re.compile(label))
            if elem:
                parent = elem.parent
                if parent:
                    text = parent.get_text()
                    match = re.search(f'{label}[:\s]*(.+?)(?=\n|$|导演|编剧|主演|类型|地区|语言)', text, re.DOTALL)
                    if match:
                        value = self._clean_text(match.group(1))
                        if value:
                            info.set(field, value)
                            continue
            
            # 备选：使用正则表达式从info_text中提取
            pattern = re.compile(f'{label}[:\s]*([^\n]+)')
            match = pattern.search(info_text)
            if match:
                value = self._clean_text(match.group(1))
                if value:
                    info.set(field, value)
    
    def _extract_summary(self, soup: BeautifulSoup, info: MovieInfo) -> None:
        """提取剧情简介"""
        summary_selectors = [
            '[property="v:summary"]',
            '.related-info .indent',
            '#link-report',
            '.intro',
            'div[class*="summary"]'
        ]
        
        for selector in summary_selectors:
            elem = soup.select_one(selector)
            if elem:
                summary = elem.get_text(strip=True)
                if summary:
                    summary = re.sub(r'\s+', ' ', summary)
                    if len(summary) > 500:
                        summary = summary[:500] + '...'
                    info.set(MovieField.SUMMARY, summary)
                    break
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ''
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        text = re.sub(r'[\n\r\t]+', ' ', text)
        return text