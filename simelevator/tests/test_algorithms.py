from __future__ import annotations

import unittest

from algorithms import REGISTRY
from algorithms.base import (
    expected_cost_floor,
    weighted_argmax,
    weighted_median,
)
from core.models import SimConfig
from core.simulator import Simulation
from algorithms import create_strategy


class HelperTests(unittest.TestCase):
    def test_median_uniform_odd(self) -> None:
        weights = {f: 1.0 for f in range(1, 12)}
        self.assertEqual(weighted_median(weights), 6)

    def test_median_uniform_even(self) -> None:
        weights = {f: 1.0 for f in range(1, 11)}
        self.assertIn(weighted_median(weights), (5, 6))

    def test_median_concentrated(self) -> None:
        weights = {1: 0.1, 5: 0.1, 9: 0.6, 10: 0.1, 11: 0.1}
        self.assertEqual(weighted_median(weights), 9)

    def test_median_skew(self) -> None:
        weights = {1: 0.4, 2: 0.3, 10: 0.3}
        self.assertEqual(weighted_median(weights), 2)

    def test_argmax(self) -> None:
        weights = {1: 0.1, 4: 0.7, 8: 0.2}
        self.assertEqual(weighted_argmax(weights), 4)

    def test_expected_cost_zero_energy_matches_median(self) -> None:
        weights = {1: 0.1, 2: 0.2, 3: 0.05, 7: 0.35, 10: 0.3}
        median = weighted_median(weights)
        floor = expected_cost_floor(
            weights, energy_weight=0.0, speed=2.0, elevator_floor=1.0
        )
        self.assertEqual(floor, median)

    def test_expected_cost_energy_pulls_toward_car(self) -> None:
        weights = {f: 1.0 for f in range(1, 11)}
        floor = expected_cost_floor(
            weights, energy_weight=0.99, speed=2.0, elevator_floor=2.0
        )
        self.assertEqual(floor, 2)


class RegistryTests(unittest.TestCase):
    def test_seven_strategies(self) -> None:
        expected = {
            "algo.stay",
            "algo.lobby",
            "algo.mode",
            "algo.median",
            "algo.expected_cost",
            "algo.zoned",
            "algo.adaptive",
        }
        self.assertEqual(set(REGISTRY), expected)

    def test_create_all(self) -> None:
        for key in REGISTRY:
            strategy = create_strategy(key)
            self.assertEqual(strategy.key, key)


class StrategyBehaviourTests(unittest.TestCase):
    def make_sim(self, key: str, **cfg_kwargs) -> Simulation:
        base = dict(floors=9, elevators=3, arrival_rate=0.0, seed=5)
        base.update(cfg_kwargs)
        return Simulation(SimConfig(**base), create_strategy(key))

    def test_lobby_parks_at_one(self) -> None:
        sim = self.make_sim("algo.lobby")
        sim.elevators[0].floor = 7.0
        self.assertEqual(sim.strategy.decide(sim.elevators[0], sim), 1)

    def test_median_on_history(self) -> None:
        sim = self.make_sim("algo.median")
        for _ in range(80):
            sim.arrival_log.append((sim.now, 8))
        for _ in range(20):
            sim.arrival_log.append((sim.now, 1))
        self.assertEqual(sim.strategy.decide(sim.elevators[0], sim), 8)

    def test_zoned_spreads_cars(self) -> None:
        sim = self.make_sim("algo.zoned")
        floors = [
            sim.strategy.decide(e, sim) for e in sim.elevators
        ]
        self.assertEqual(len(set(floors)), len(floors))
        self.assertEqual(min(floors), 1)
        self.assertEqual(max(floors), 9)

    def test_stay_returns_current(self) -> None:
        sim = self.make_sim("algo.stay")
        sim.elevators[0].floor = 4.0
        self.assertEqual(sim.strategy.decide(sim.elevators[0], sim), 4)


if __name__ == "__main__":
    unittest.main()
