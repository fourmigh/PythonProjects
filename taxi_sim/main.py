"""入口: 初始化配置/数据库/SDK管理器/主窗口。
首次运行未配置任何 Key 时自动弹出设置界面引导。
"""
import logging
import sys

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app_config import AppConfig  # noqa: E402
from i18n import set_language  # noqa: E402
from data import store  # noqa: E402
from mapsdk.manager import MapManager  # noqa: E402
from sim.engine import SimulationEngine  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.settings_dialog import SettingsDialog  # noqa: E402


def main():
    config = AppConfig()
    set_language(config.language)
    store.init()
    manager = MapManager(config)
    engine = SimulationEngine(manager, config)

    app = QApplication(sys.argv)
    win = MainWindow(config, manager, engine)
    win.show()

    if not config.any_key:
        dlg = SettingsDialog(config, manager, win.map, win)
        accepted = dlg.exec()
        win._refresh_ui_ready()
        if accepted and config.any_key:
            win.map.load_city(win._current_city_obj())
        elif not config.any_key:
            logging.info("未配置 Key: 界面已锁定, 请通过菜单 系统>设置 填写")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
