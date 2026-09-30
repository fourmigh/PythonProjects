from __future__ import annotations

from abc import ABC, abstractmethod

REGISTRY: dict[str, type["ParkingStrategy"]] = {}


def register(cls: type["ParkingStrategy"]) -> type["ParkingStrategy"]:
    REGISTRY[cls.key] = cls
    return cls


class ParkingStrategy(ABC):
    key: str = ""

    @abstractmethod
    def decide(self, elevator, sim) -> int:
        raise NotImplementedError

    def reset(self) -> None:
        pass


def weighted_median(weights: dict[int, float]) -> int:
    items = sorted((f, w) for f, w in weights.items() if w > 0)
    if not items:
        return 1
    total = sum(w for _, w in items)
    half = total / 2.0
    acc = 0.0
    for f, w in items:
        acc += w
        if acc >= half:
            return f
    return items[-1][0]


def weighted_argmax(weights: dict[int, float]) -> int:
    best_f = 1
    best_w = float("-inf")
    for f in sorted(weights):
        if weights[f] > best_w:
            best_w = weights[f]
            best_f = f
    return best_f


def travel_time(a: float, b: float, speed: float) -> float:
    return abs(a - b) / max(speed, 1e-6)


def expected_cost_floor(
    weights: dict[int, float],
    energy_weight: float,
    speed: float,
    elevator_floor: float,
) -> int:
    best_f = 1
    best_cost = float("inf")
    for f in weights:
        wait_term = sum(
            w * travel_time(y, f, speed) for y, w in weights.items()
        )
        energy_term = travel_time(elevator_floor, f, speed)
        cost = (1.0 - energy_weight) * wait_term + energy_weight * energy_term
        if cost < best_cost - 1e-12:
            best_cost = cost
            best_f = f
    return best_f
