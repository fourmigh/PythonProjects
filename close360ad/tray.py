import pystray
from PIL import Image, ImageDraw


_icon = None
_show_stats_cb = None
_show_procs_cb = None


def set_show_stats_callback(cb):
    global _show_stats_cb
    _show_stats_cb = cb


def set_show_procs_callback(cb):
    global _show_procs_cb
    _show_procs_cb = cb


def notify(title, message):
    if _icon:
        _icon.notify(message, title)


def set_tooltip(text):
    if _icon:
        _icon.title = text


def _create_image():
    w, h = 64, 64
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, w - 4, h - 4], fill='#CC0000', outline='#880000', width=3)
    draw.line([16, 16, 48, 48], fill='white', width=6)
    draw.line([48, 16, 16, 48], fill='white', width=6)
    return img


def run_tray(stop_event, pause_event):
    global _icon

    def on_scan(icon, item):
        from hunter import find_and_close_ads
        find_and_close_ads()

    def on_toggle(icon, item):
        if pause_event.is_set():
            pause_event.clear()
            icon.title = 'Close360Ad - 正在运行'
        else:
            pause_event.set()
            icon.title = 'Close360Ad [已暂停]'

    def on_stats(icon, item):
        if _show_stats_cb:
            _show_stats_cb()

    def on_procs(icon, item):
        if _show_procs_cb:
            _show_procs_cb()

    def on_exit(icon, item):
        stop_event.set()
        icon.stop()

    image = _create_image()
    menu = pystray.Menu(
        pystray.MenuItem('立即扫描', on_scan),
        pystray.MenuItem('显示统计', on_stats),
        pystray.MenuItem('进程列表', on_procs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            lambda _: '⏸ 暂停监控' if not pause_event.is_set() else '▶ 继续监控',
            on_toggle,
            checked=lambda _: not pause_event.is_set()
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('退出', on_exit),
    )

    _icon = pystray.Icon('close360ad', image, 'Close360Ad - 正在运行', menu)
    _icon.run()
