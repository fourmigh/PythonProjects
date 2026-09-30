from __future__ import annotations

import random
from dataclasses import dataclass

from core.building import PEOPLE_KINDS
from core.models import DEFAULT_PEOPLE_KIND, SimConfig


@dataclass(frozen=True)
class PassengerEvent:
    pid: int
    origin: int
    dest: int
    time: float
    deadline: float | None = None
    #: 男/女/儿童/轮椅，只影响界面显示
    gender: str = DEFAULT_PEOPLE_KIND


def _random_gender(seed: int, pid: int) -> str:
    """随机到达模式下由 (种子, 乘客号) 确定性推导人群分类。

    刻意不消耗 self.rng：到达时刻与楼层的随机序列必须与加这个字段之前
    完全一致，否则所有既有仿真结果都会平移。
    """
    rng = random.Random(f"gender|{seed}|{pid}")
    return rng.choice(PEOPLE_KINDS)


def _parse_weights(text: str, n: int) -> list[float]:
    parts: list[float] = []
    for chunk in text.replace("，", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            parts.append(max(0.0, float(chunk)))
        except ValueError:
            parts.append(0.0)
    if len(parts) < n:
        parts = parts + [1.0] * (n - len(parts))
    return parts[:n]


class PassengerGenerator:
    def __init__(self, config: SimConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self._pid = 0
        self._next_time = 0.0
        self._queue: list[PassengerEvent] = []
        self._origin_weights = self._build_origin_weights()
        self._seed_first()

    def _build_origin_weights(self) -> list[float]:
        cfg = self.config
        floors = cfg.floors
        if cfg.origin_mode == "custom":
            weights = _parse_weights(cfg.custom_origin_weights, floors)
            if sum(weights) <= 0:
                return [1.0] * floors
            return weights
        if cfg.origin_mode == "lobby":
            lobby = max(1, min(floors, 1))
            weights = [1.0] * floors
            others = floors - 1
            per_other = (1.0 - cfg.lobby_share) / others if others else 0.0
            for i in range(floors):
                weights[i] = per_other
            weights[lobby - 1] = cfg.lobby_share
            return weights
        return [1.0] * floors

    def _build_dest_weights(self, origin: int) -> list[float]:
        cfg = self.config
        floors = cfg.floors
        if cfg.dest_mode == "custom":
            weights = _parse_weights(cfg.custom_dest_weights, floors)
            if sum(weights) <= 0:
                weights = [1.0] * floors
        elif cfg.dest_mode == "lobby":
            weights = [1.0] * floors
            others = floors - 1
            per_other = (1.0 - cfg.dest_lobby_share) / others if others else 0.0
            for i in range(floors):
                weights[i] = per_other
            weights[0] = cfg.dest_lobby_share
        else:
            weights = [1.0] * floors
        weights = list(weights)
        weights[origin - 1] = 0.0
        if sum(weights) <= 0:
            for i in range(floors):
                if i != origin - 1:
                    weights[i] = 1.0
        return weights

    def _seed_first(self) -> None:
        self._advance()

    def _advance(self) -> None:
        cfg = self.config
        if cfg.arrival_rate <= 0:
            self._next_time = float("inf")
            return
        mean_gap = 60.0 / cfg.arrival_rate
        self._next_time += self.rng.expovariate(1.0 / mean_gap)
        origin = self.rng.choices(
            range(1, cfg.floors + 1), weights=self._origin_weights, k=1
        )[0]
        dest_weights = self._build_dest_weights(origin)
        dest = self.rng.choices(
            range(1, cfg.floors + 1), weights=dest_weights, k=1
        )[0]
        if dest == origin:
            dest = origin % cfg.floors + 1
        self._queue.append(
            PassengerEvent(
                pid=self._pid,
                origin=origin,
                dest=dest,
                time=self._next_time,
                gender=_random_gender(cfg.seed, self._pid),
            )
        )
        self._pid += 1

    def next_time(self, now: float | None = None) -> float:
        """下一个乘客事件的时刻，供自适应时间步进在空闲时精确停步。

        随机到达的下一事件是绝对时刻，与 now 无关，故忽略该参数；
        保留形参是为了和 ProfileGenerator 保持同一接口。
        """
        del now
        if self._queue:
            return self._queue[0].time
        return self._next_time

    def pop_until(self, now: float) -> list[PassengerEvent]:
        out: list[PassengerEvent] = []
        while self._queue and self._queue[0].time <= now:
            out.append(self._queue.pop(0))
        while self._next_time <= now and self._next_time != float("inf"):
            self._advance()
            if self._queue and self._queue[0].time <= now:
                out.append(self._queue.pop(0))
            else:
                break
        return out
