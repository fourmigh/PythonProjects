"""UI模块 - 图形用户界面"""

from ui.parkinggui import ParkingGUI
from ui.spot_status_window import SpotStatusWindow
from ui.system_proxy import system_proxy, ParkingSystemProxy
from ui.shared_utils import (
    COLORS,
    get_legends,
    get_spot_status_legends,
    get_current_date_str,
    format_time_range,
    create_legend_frame,
    create_header,
    create_scrollable_area
)

__all__ = [
    'ParkingGUI',
    'SpotStatusWindow',
    'system_proxy',
    'ParkingSystemProxy',
    'COLORS',
    'get_legends',
    'get_spot_status_legends',
    'get_current_date_str',
    'format_time_range',
    'create_legend_frame',
    'create_header',
    'create_scrollable_area'
]