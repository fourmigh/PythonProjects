"""Playwright 浏览器管理器 - 使用真实浏览器获取页面"""

from playwright.sync_api import sync_playwright


class BrowserFetcher:
    """使用 Playwright Firefox 获取渲染后的页面 HTML"""

    def __init__(self, headless: bool = True):
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.firefox.launch(headless=headless)
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
                "Gecko/20100101 Firefox/128.0"
            ),
            locale="zh-CN",
        )
        self.page = self.context.new_page()

    def get_html(self, url: str, timeout: int = 60000) -> str:
        """访问 URL 并等待 PoW 挑战解决后返回 HTML"""
        self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")

        # 检测 PoW 挑战页（包含 #sec 表单）
        if self.page.query_selector('#sec'):
            print("  检测到 PoW 挑战，等待浏览器自动求解...")
            self.page.wait_for_function(
                "() => !document.querySelector('#sec')",
                timeout=timeout
            )
            print("  挑战完成")

        # 等待真实内容加载（#content 或 #wrapper 是豆瓣页面通用容器）
        self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
        try:
            self.page.wait_for_selector('#content, #wrapper', timeout=15000)
        except Exception:
            pass
        self.page.wait_for_timeout(1000)
        return self.page.content()

    def close(self) -> None:
        """关闭浏览器"""
        try:
            self.context.close()
        except Exception:
            pass
        try:
            self.browser.close()
        except Exception:
            pass
        self._playwright.stop()