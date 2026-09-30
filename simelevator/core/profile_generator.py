from __future__ import annotations

import random
from collections import deque

from core.models import DEFAULT_PEOPLE_KIND, SimConfig
from core.passenger import PassengerEvent
from core.profiles import (
    MINUTES_PER_DAY,
    RESIDENT,
    VISITOR,
    PassengerProfile,
    derive_seed,
    resolve,
)

DAY_SECONDS = 86400.0
MEET_DELAY_MIN = 5


class ProfileGenerator:
    def __init__(
        self,
        config: SimConfig,
        profiles: list[PassengerProfile],
    ):
        self.config = config
        self.profiles = [
            resolve(p, config.floors, config.seed) for p in profiles
        ]
        # deque 而非 list：每天数千个事件，list.pop(0) 是 O(n) 搬移
        self._queue: deque[PassengerEvent] = deque()
        self._next_day = 0
        self._pid = 0

    @property
    def _start_sec(self) -> float:
        return float(self.config.start_time_min % MINUTES_PER_DAY) * 60.0

    def _day_of(self, day: int) -> int:
        return (self.config.start_weekday - 1 + day) % 7 + 1

    @staticmethod
    def _min_to_sec(minute: int) -> float:
        return float(minute % MINUTES_PER_DAY) * 60.0

    def _resident_trips(self, profile: PassengerProfile) -> list[tuple[float, int, int]]:
        home = int(profile.home_floor or 1)
        out: list[tuple[float, int, int]] = []
        position = home
        for leg in profile.legs:
            target = int(leg.target_floor or home)
            if target != position:
                out.append((self._min_to_sec(int(leg.time_min or 0)), position, target))
                position = target
        if position != home:
            last = profile.legs[-1] if profile.legs else None
            back_at = int(last.time_min or 0) + int(last.stay_min or 0) if last else 0
            out.append((self._min_to_sec(back_at), position, home))
        return out

    def _visitor_trips(self, profile: PassengerProfile) -> list[tuple[float, int, int]]:
        target = int(profile.main_floor or 2)
        delay = MEET_DELAY_MIN if profile.needs_meet else 0
        up_at = self._min_to_sec(int(profile.visitor_arrive or 0) + delay)
        down_at = up_at + float(profile.visitor_stay or 60) * 60.0
        return [(up_at, 1, target), (down_at, target, 1)]

    def _generate_day(self, day: int) -> list[PassengerEvent]:
        day_start = day * DAY_SECONDS - self._start_sec
        weekday = self._day_of(day)
        events: list[PassengerEvent] = []
        for profile in self.profiles:
            if profile.weekdays and weekday not in profile.weekdays:
                continue
            rng = random.Random(derive_seed(self.config.seed + day * 100003, profile.pid, profile.name))
            attendance = float(
                profile.attendance if profile.attendance is not None else 1.0
            )
            if rng.random() > attendance:
                continue
            if profile.kind == RESIDENT:
                trips = self._resident_trips(profile)
            elif profile.kind == VISITOR:
                trips = self._visitor_trips(profile)
            else:
                continue
            companions = int(profile.companions or 1)
            jitter_sec = float(profile.jitter_min or 0) * 60.0
            # resolve() 已保证 gender 合法；同组结伴者共用同一个分类
            gender = profile.gender or DEFAULT_PEOPLE_KIND
            for offset, origin, dest in trips:
                jitter = rng.uniform(-jitter_sec, jitter_sec) if jitter_sec > 0 else 0.0
                when = day_start + offset + jitter
                if when < 0.0:
                    continue
                deadline = when + float(profile.abandon_sec or 60.0)
                for _ in range(companions):
                    events.append(
                        PassengerEvent(
                            pid=self._pid,
                            origin=origin,
                            dest=dest,
                            time=when,
                            deadline=deadline,
                            gender=gender,
                        )
                    )
                    self._pid += 1
        events.sort(key=lambda e: (e.time, e.pid))
        return events

    def _ensure_generated(self, now: float) -> None:
        """按 pop_until 的同一天界线补足队列。

        提前生成不会破坏确定性：_generate_day 用 seed+day 定种，
        与它被调用的时机无关。
        """
        clock_now = self._start_sec + now
        target_day = int(clock_now // DAY_SECONDS) + 1
        while self._next_day < target_day:
            self._queue.extend(self._generate_day(self._next_day))
            self._next_day += 1

    def next_time(self, now: float) -> float:
        """now 之后下一个乘客事件的时刻；没有画像时返回无穷大。"""
        self._ensure_generated(now)
        return self._queue[0].time if self._queue else float("inf")

    def pop_until(self, now: float) -> list[PassengerEvent]:
        self._ensure_generated(now)
        out: list[PassengerEvent] = []
        while self._queue and self._queue[0].time <= now:
            out.append(self._queue.popleft())
        return out
