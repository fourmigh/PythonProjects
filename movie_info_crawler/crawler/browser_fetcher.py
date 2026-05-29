"""Playwright 浏览器管理器 - 使用真实浏览器获取页面"""

import time
from typing import Optional

from playwright.sync_api import sync_playwright


class BrowserFetcher:
    """使用 Playwright Firefox 获取渲染后的页面 HTML"""

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._playwright = sync_playwright().start()
        self._launch_browser(headless)

    @property
    def is_headless(self) -> bool:
        return self._headless

    def get_html(self, url: str, timeout: int = 120000,
                 wait_for_data: bool = False,
                 wait_for_selector: Optional[str] = None,
                 wait_until: str = "commit") -> str:
        """访问 URL 并等待各种挑战解决后返回 HTML"""
        self.page.goto(url, timeout=timeout, wait_until=wait_until)

        # 检测 PoW 挑战页（包含 #sec 表单）
        if self.page.query_selector('#sec'):
            print("  检测到 PoW 挑战，等待浏览器自动求解...")
            self.page.wait_for_function(
                "() => !document.querySelector('#sec')",
                timeout=timeout
            )
            print("  挑战完成")

        # 检测腾讯滑块验证码
        if self._detect_captcha():
            if self._is_rate_limited():
                print("  验证码限流: 操作过于频繁，跳过")
                self.page.wait_for_timeout(1000)
                return self.page.content()
            passed = self._wait_for_captcha_complete(timeout)
            if not passed:
                if self._headless:
                    print("  切换到可见浏览器，请手动完成验证码...")
                    self.restart_browser(headless=False)
                    self.page.goto(url, timeout=timeout, wait_until=wait_until)
                input("  请在浏览器中完成验证码后按回车继续...")
                self._wait_for_captcha_complete(60000)
            print("  验证码已通过")

        # 等待页面数据就绪（仅搜索页有 __DATA__）
        if wait_for_data:
            self.page.wait_for_function(
                '() => typeof window.__DATA__ !== "undefined"',
                timeout=timeout
            )

        # 等待 JS 渲染指定元素
        if wait_for_selector:
            self.page.wait_for_selector(wait_for_selector, timeout=timeout)

        self.page.wait_for_timeout(1000)
        return self.page.content()

    def _detect_captcha(self) -> bool:
        url = self.page.url.lower()
        if 'myasverify' in url or 'yamaha' in url:
            return True
        return self.page.evaluate('''() => {
            return !!(
                document.querySelector('.tencent-captcha') ||
                document.querySelector('iframe[src*="captcha"]') ||
                document.querySelector('[class*="tencent-captcha"]')
            );
        }''')

    def _is_rate_limited(self) -> bool:
        try:
            return self.page.evaluate('''() => {
                const text = document.body.innerText || '';
                return text.includes('操作过于频繁');
            }''')
        except Exception:
            return False

    def _launch_browser(self, headless: bool) -> None:
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

    def restart_browser(self, headless: bool) -> None:
        self.close_browser()
        self._launch_browser(headless)
        self._headless = headless

    def _wait_for_captcha_complete(self, timeout: int) -> bool:
        deadline = time.time() + timeout / 1000
        while time.time() < deadline:
            current = self.page.url.lower()
            has_captcha_url = 'myasverify' in current or 'yamaha' in current
            has_captcha_el = self.page.evaluate('''() => {
                const el = document.querySelector(
                    '.tencent-captcha, [class*="tencent-captcha"], iframe[src*="captcha"]'
                );
                return el ? true : false;
            }''')
            if not has_captcha_url and not has_captcha_el:
                return True
            time.sleep(0.5)
        return False

    def close_browser(self) -> None:
        """仅关闭浏览器（保留 Playwright），用于切换 headless/visible"""
        try:
            self.context.close()
        except Exception:
            pass
        try:
            self.browser.close()
        except Exception:
            pass

    def close(self) -> None:
        """完全关闭（浏览器 + Playwright），程序退出时调用"""
        self.close_browser()
        try:
            self._playwright.stop()
        except Exception:
            pass