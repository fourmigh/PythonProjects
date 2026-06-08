import sys
import os
import random
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.browser_fetcher import BrowserFetcher
from crawler.config_manager import ConfigManager
from crawler.db_search import DbSearch
from crawler.info_extractor import InfoExtractor
from crawler.my_extractor import MyExtractor
from crawler.html_generator import HTMLGenerator
from crawler.models import MovieResult, UserChoice, MovieField, Source


class MovieInfoCrawler:
    def __init__(self, config_dir: str = '.'):
        self.config = ConfigManager(config_dir)
        self.browser = None
        self.db_search = None
        self.extractor = None
        self.my = None
        self.results: list = []
        self._douban_headless = True
        self._maoyan_headless = True

    def run(self) -> None:
        try:
            self._print_banner()

            if not self.config.movies:
                print("[错误] 配置文件中没有电影列表，请先配置 config.json")
                return

            self._scrape_all_movies()

            selected_fields = self._select_fields()

            generator = HTMLGenerator(self.config)
            output_file = generator.generate(self.results, fields=selected_fields)
            print(f"\n[成功] HTML报告已生成: {output_file}")

            print(f"\n[完成] 程序执行完毕！报告路径: {output_file}")
        finally:
            if self.browser:
                self.browser.close()

    def _print_banner(self) -> None:
        print("=" * 70)
        print("MovieInfoCrawler - 电影信息爬取工具")
        print("=" * 70)
        print(f"配置文件目录: 当前目录")
        print(f"电影数量: {len(self.config.movies)}")
        print("=" * 70)

        self._ensure_browser_mode(self._douban_headless)

    def _init_browser(self, headless: bool = True) -> None:
        from crawler.browser_fetcher import BrowserFetcher
        from crawler.db_search import DbSearch
        from crawler.info_extractor import InfoExtractor
        from crawler.my_extractor import MyExtractor
        self.browser = BrowserFetcher(headless=headless)
        self.db_search = DbSearch(self.config, self.browser)
        self.extractor = InfoExtractor(self.config, self.browser)
        self.my = MyExtractor(self.config, self.browser)

    def _ensure_browser_mode(self, headless: bool) -> None:
        if self.browser is None or self.browser.is_headless != headless:
            if self.browser:
                print(f"  [浏览器] 切换至 {'可见' if not headless else 'headless'} 模式")
                self.browser.restart_browser(headless)
            else:
                print(f"  [浏览器] 启动 {'可见' if not headless else 'headless'} 模式")
                self._init_browser(headless=headless)

    def _search_and_choose(
        self, movie_name: str, source_name: str, searcher,
        auto_single: bool = False
    ) -> str:
        """搜索→(用户选择)，返回 URL 或空字符串"""
        results = searcher.search(movie_name)
        if not results:
            print(f"   未找到{source_name}页面")
            return ''

        if len(results) == 1 and auto_single:
            selected = results[0]
            print(f"   已选择: {selected.title}")
            return selected.url

        choice = self._get_user_choice(movie_name, results)
        if choice.type == 'skip':
            return ''

        if choice.type == 'select':
            selected = results[choice.index]
            print(f"   已选择: {selected.title} ({selected.year})")
            return selected.url
        else:
            print(f"   使用手动链接: {choice.url}")
            return choice.url

    def _scrape_all_movies(self) -> None:
        for i, movie_name in enumerate(self.config.movies, 1):
            if i > 1:
                delay = random.uniform(3, 6)
                print(f"  等待 {delay:.1f} 秒避免限频...")
                time.sleep(delay)
            print(f"\n[{i}/{len(self.config.movies)}] 正在处理: {movie_name}")
            print("-" * 40)

            maoyan_info = None
            self._ensure_browser_mode(self._maoyan_headless)
            maoyan_url = self._search_and_choose(movie_name, '猫眼', self.my, auto_single=True)
            if maoyan_url:
                maoyan_info = self.my.extract(maoyan_url)
                if maoyan_info:
                    maoyan_fields = [f.label for f in MovieField if maoyan_info.get(f, Source.MAOYAN)]
                    if maoyan_fields:
                        print(f"   猫眼提取到字段: {', '.join(maoyan_fields)}")
            else:
                print(f"   未找到猫眼页面")

            self._ensure_browser_mode(self._douban_headless)
            url = self._search_and_choose(movie_name, '豆瓣', self.db_search)
            if not url:
                self.results.append(MovieResult(
                    search_name=movie_name, found=False, error="未找到或用户跳过"
                ))
                continue

            info = self.extractor.extract(url)
            if not info:
                print(f"   [失败] 提取失败，退出程序")
                sys.exit(1)

            title = info.get_by_label('片名') or movie_name
            print(f"   成功提取《{title}》的信息")
            douban_fields = [f.label for f in MovieField if info.get(f, Source.DOUBAN)]
            if douban_fields:
                print(f"   豆瓣提取到字段: {', '.join(douban_fields)}")

            if maoyan_info:
                info.merge(maoyan_info)
                maoyan_fields = [f.label for f in MovieField if info.get(f, Source.MAOYAN)]
                if maoyan_fields:
                    print(f"   猫眼数据已合并")
                    print(f"   猫眼提取到字段: {', '.join(maoyan_fields)}")
                else:
                    print(f"   猫眼数据已合并（无新字段）")

            self.results.append(MovieResult(
                search_name=movie_name, found=True, info=info
            ))

    def _select_fields(self) -> list:
        all_fields = [f for f in MovieField if f not in (MovieField.TITLE, MovieField.DOUBAN_LINK)]
        selected = set(all_fields)

        print("\n选择要显示的字段（默认全部显示，输入编号取消）:")
        for i, field in enumerate(all_fields, 1):
            print(f"  {i:2d}. {field.label}")
        print("直接回车全部显示，或输入要取消的编号（逗号分隔）:")
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return list(all_fields)

        if not line:
            return list(all_fields)

        for part in line.replace('，', ',').split(','):
            part = part.strip()
            try:
                idx = int(part) - 1
                if 0 <= idx < len(all_fields):
                    selected.discard(all_fields[idx])
            except ValueError:
                pass

        result = [f for f in all_fields if f in selected]
        hidden = [f.label for f in all_fields if f not in selected]
        if hidden:
            print(f"  已取消: {', '.join(hidden)}")
        return result

    @staticmethod
    def _kbhit() -> bool:
        if sys.platform == 'win32':
            import msvcrt
            return msvcrt.kbhit()
        import select
        r, _, _ = select.select([sys.stdin], [], [], 0)
        return bool(r)

    @staticmethod
    def _getch() -> str:
        if sys.platform == 'win32':
            import msvcrt
            return msvcrt.getch().decode('utf-8', errors='ignore')
        import select
        r, _, _ = select.select([sys.stdin], [], [], 0.1)
        if r:
            return sys.stdin.read(1)
        return ''

    def _get_user_choice(self, movie_name: str, search_results: list) -> UserChoice:
        print(f"\n   搜索到 {len(search_results)} 个相关结果：")
        print("   " + "-" * 56)

        for i, result in enumerate(search_results, 1):
            year_info = f" ({result.year})" if result.year else ""
            print(f"   {i}. {result.title}{year_info}")
            print(f"      {result.url}")

        print(f"   {len(search_results)+1}. 手动输入链接")
        print(f"   {len(search_results)+2}. [跳过] 跳过此电影")
        print("   " + "-" * 56)

        line = ''
        for remaining in range(5, 0, -1):
            sys.stdout.write(f"\r   请选择 (将在 {remaining} 秒后自动选择第 1 项): ")
            sys.stdout.flush()
            deadline = time.time() + 1
            while time.time() < deadline:
                if self._kbhit():
                    ch = self._getch()
                    if ch in ('\r', '\n'):
                        print()
                        break
                    elif ch == '\x08' and line:
                        line = line[:-1]
                    elif ch.isdigit():
                        line += ch
                        print()
                        break
                    sys.stdout.write(f"\r   请选择 (将在 {remaining} 秒后自动选择第 1 项): {line}  ")
                    sys.stdout.flush()
                time.sleep(0.05)
            else:
                continue
            break
        else:
            print(f"\r   自动选择: 1{' ' * 50}")
            return UserChoice(type='select', index=0)

        line = line.strip()
        while True:
            choice = line or input("   请选择: ").strip()
            line = ''
            if not choice:
                continue

            try:
                choice_num = int(choice)
            except ValueError:
                print("   请输入有效数字")
                continue

            if 1 <= choice_num <= len(search_results):
                return UserChoice(type='select', index=choice_num - 1)
            elif choice_num == len(search_results) + 1:
                manual_url = input("   请输入链接: ").strip()
                if manual_url:
                    return UserChoice(type='manual', url=manual_url)
                print("   链接格式不正确")
                continue
            elif choice_num == len(search_results) + 2:
                return UserChoice(type='skip')
            else:
                print(f"   请输入 1-{len(search_results)+2} 之间的数字")

if __name__ == "__main__":
    crawler = MovieInfoCrawler()
    crawler.run()
