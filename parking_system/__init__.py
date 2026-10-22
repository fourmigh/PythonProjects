"""自行车停车库预订系统"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import (
    ParkingSystem,
    AllocationManager,
    AllocationWeights,
    User,
    UserStatus,
    TimeSlotStatus,
    calculate_bitmap,
    has_overlap
)

from ui import (
    ParkingGUI,
    SpotStatusWindow,
    system_proxy,
    COLORS,
    get_current_date_str
)

__version__ = '1.0.0'
__author__ = 'Parking System Team'

__all__ = [
    # Core模块
    'ParkingSystem',
    'AllocationManager',
    'AllocationWeights',
    'User',
    'UserStatus',
    'TimeSlotStatus',
    'calculate_bitmap',
    'has_overlap',
    # UI模块
    'ParkingGUI',
    'SpotStatusWindow',
    'system_proxy',
    'COLORS',
    'get_current_date_str'
]