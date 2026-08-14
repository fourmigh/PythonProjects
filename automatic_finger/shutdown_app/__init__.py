"""电源助手应用包（自带独立构建脚本 shutdown_app.bat）。

- engine.py: 电源引擎（任务栏几何锚点 + OCR 定位 + 人形鼠标点击，支持睡眠/关机/重启）
- gui.py:    界面入口（打包目标）
"""

from .engine import (
    DEFAULT_PARAMS,
    compute_anchors,
    detect_env,
    ensure_elevated,
    is_process_elevated,
    run_shutdown_flow,
)

__all__ = [
    "DEFAULT_PARAMS",
    "compute_anchors",
    "detect_env",
    "ensure_elevated",
    "is_process_elevated",
    "run_shutdown_flow",
]