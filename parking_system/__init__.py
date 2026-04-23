"""自行车停车库预订系统"""

from core import (
    ParkingSystem,
    AllocationManager,
    AllocationWeights,
    User,
    UserStatus,
    TimeSlotStatus,
    calculate_bitmap,
    has_overlap,
    get_conflict_range,
    format_slots
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
    'get_conflict_range',
    'format_slots',
    # UI模块
    'ParkingGUI',
    'SpotStatusWindow',
    'system_proxy',
    'COLORS',
    'get_current_date_str'
]