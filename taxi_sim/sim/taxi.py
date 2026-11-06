"""出租车 Agent 状态机: cruising → to_passenger(空驶) → onboard(载客) → cruising。
位置沿路线折线按速度逐帧推进。
"""
from data import roads

SPEED_KMH = 30.0  # 市区平均车速


class Taxi:
    __slots__ = ("tid", "position", "state", "route", "route_idx",
                 "target", "passenger", "strategy", "idle_since", "busy_time")

    CRUISING = "cruising"
    TO_PASSENGER = "to_passenger"
    ONBOARD = "onboard"

    def __init__(self, tid, position, strategy):
        self.tid = tid
        self.position = position
        self.state = self.CRUISING
        self.route = None          # [(lat,lng)...]
        self.route_idx = 0
        self.target = None
        self.passenger = None
        self.strategy = strategy
        self.idle_since = 0.0
        self.busy_time = 0.0

    def set_route(self, points, target=None):
        if points and len(points) >= 2:
            self.route = points
            self.route_idx = 0
            self.target = target
            return True
        return False

    def clear_route(self):
        self.route = None
        self.route_idx = 0
        self.target = None

    def advance(self, dt):
        """沿路线推进 dt 秒, 返回 True 表示已到达终点。"""
        if not self.route:
            return True
        meters = SPEED_KMH / 3.6 * dt
        i = self.route_idx
        while meters > 0 and i < len(self.route) - 1:
            a = self.route[i]
            b = self.route[i + 1]
            seg_m = roads.deg_to_m(a, b)
            if seg_m <= 1e-9:
                i += 1
                continue
            remain = roads.deg_to_m(self.position, b)
            if remain > meters:
                # 已走到 seg_m-remain 处, 再前进 meters → 按比例推进
                frac = (seg_m - remain + meters) / seg_m
                frac = max(0.0, min(1.0, frac))
                self.position = (a[0] + (b[0] - a[0]) * frac,
                                 a[1] + (b[1] - a[1]) * frac)
                self.route_idx = i
                return False
            meters -= remain
            self.position = b
            i += 1
        self.route_idx = max(0, i - 1)
        if i >= len(self.route) - 1:
            self.position = self.route[-1]
            return True
        return False
