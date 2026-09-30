from __future__ import annotations

from algorithms.base import (
    ParkingStrategy,
    expected_cost_floor,
    register,
    weighted_argmax,
    weighted_median,
)


@register
class StayStrategy(ParkingStrategy):
    key = "algo.stay"

    def decide(self, elevator, sim) -> int:
        return int(round(elevator.floor))


@register
class LobbyStrategy(ParkingStrategy):
    key = "algo.lobby"

    def decide(self, elevator, sim) -> int:
        return 1


@register
class ModeStrategy(ParkingStrategy):
    key = "algo.mode"

    def decide(self, elevator, sim) -> int:
        return weighted_argmax(sim.call_distribution())


@register
class MedianStrategy(ParkingStrategy):
    key = "algo.median"

    def decide(self, elevator, sim) -> int:
        return weighted_median(sim.call_distribution())


@register
class ExpectedCostStrategy(ParkingStrategy):
    key = "algo.expected_cost"

    def decide(self, elevator, sim) -> int:
        return expected_cost_floor(
            sim.call_distribution(),
            sim.config.energy_weight,
            sim.config.speed,
            elevator.floor,
        )


@register
class ZonedStrategy(ParkingStrategy):
    key = "algo.zoned"

    def decide(self, elevator, sim) -> int:
        total_cars = len(sim.elevators)
        weights = sim.call_distribution()
        if total_cars <= 1:
            quantile = 0.5
        else:
            quantile = elevator.eid / (total_cars - 1)
        floors = sorted(weights)
        if not floors:
            return 1
        total = sum(weights.values())
        if total <= 0:
            index = int(round(quantile * (len(floors) - 1)))
            return floors[min(index, len(floors) - 1)]
        acc = 0.0
        for f in floors:
            acc += weights[f]
            if acc >= quantile * total:
                return f
        return floors[-1]


@register
class AdaptiveStrategy(ParkingStrategy):
    key = "algo.adaptive"
    window = 120.0

    def decide(self, elevator, sim) -> int:
        window = min(sim.config.history_window, self.window)
        return expected_cost_floor(
            sim.call_distribution(window=window),
            sim.config.energy_weight,
            sim.config.speed,
            elevator.floor,
        )
