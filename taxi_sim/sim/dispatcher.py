"""派单模块: 每帧将 空闲出租车 ↔ 等待乘客 按最近距离贪心匹配。"""
from data import roads
from sim.passenger import Passenger
from sim.taxi import Taxi


def assign(taxis, passengers, now):
    """对每个未被分配的等待乘客, 找最近空闲且无目标的出租车。
    返回 [(taxi, passenger)] 新建立的匹配。
    """
    idle = [t for t in taxis
            if t.state == Taxi.CRUISING and t.passenger is None
            and t.target is None]
    waiting = [p for p in passengers
               if p.state == Passenger.WAITING and p.assigned_taxi is None]
    matches = []
    if not idle or not waiting:
        return matches
    for p in sorted(waiting, key=lambda p: -p.wait_seconds(now)):  # 最久等者优先
        if not idle:
            break
        best = min(idle, key=lambda t: roads.hav_deg(t.position, p.origin))
        matches.append((best, p))
        idle.remove(best)
    return matches
