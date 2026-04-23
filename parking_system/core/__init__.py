"""核心模块 - 停车场系统核心逻辑"""

from core.parking_system import ParkingSystem
from core.allocation import AllocationManager
from core.config import AllocationWeights
from core.models import User, UserStatus, TimeSlotStatus
from core.utils import calculate_bitmap, has_overlap, get_conflict_range, format_slots

__all__ = [
    'ParkingSystem',
    'AllocationManager',
    'AllocationWeights',
    'User',
    'UserStatus',
    'TimeSlotStatus',
    'calculate_bitmap',
    'has_overlap',
    'get_conflict_range',
    'format_slots'
]