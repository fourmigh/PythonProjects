from __future__ import annotations

import unittest

from core.models import PassengerState, SimConfig
from core.passenger import PassengerGenerator
from core.simulator import Simulation
from algorithms import REGISTRY, create_strategy


def make_config(**kwargs) -> SimConfig:
    base = dict(
        floors=8,
        elevators=2,
        speed=2.0,
        door_time=0.5,
        boarding_time=0.4,
        alighting_time=0.3,
        min_door_open=0.5,
        arrival_rate=12.0,
        seed=7,
        idle_park_delay=1.0,
    )
    base.update(kwargs)
    return SimConfig(**base)


class PassengerGeneratorTests(unittest.TestCase):
    def test_same_seed_same_events(self) -> None:
        cfg = make_config()
        g1 = PassengerGenerator(cfg)
        g2 = PassengerGenerator(cfg)
        for t in range(0, 200):
            self.assertEqual(g1.pop_until(float(t)), g2.pop_until(float(t)))

    def test_different_seed_differs(self) -> None:
        g1 = PassengerGenerator(make_config(seed=1))
        g2 = PassengerGenerator(make_config(seed=2))
        e1 = g1.pop_until(300.0)
        e2 = g2.pop_until(300.0)
        self.assertNotEqual(
            [(e.origin, e.dest, e.time) for e in e1],
            [(e.origin, e.dest, e.time) for e in e2],
        )

    def test_dest_never_equals_origin(self) -> None:
        for seed in range(10):
            gen = PassengerGenerator(make_config(seed=seed, floors=4))
            for event in gen.pop_until(600.0):
                self.assertNotEqual(event.origin, event.dest)

    def test_lobby_mode_concentrates(self) -> None:
        gen = PassengerGenerator(make_config(origin_mode="lobby", seed=3))
        events = gen.pop_until(600.0)
        lobby_ratio = sum(1 for e in events if e.origin == 1) / len(events)
        self.assertGreater(lobby_ratio, 0.45)


class SimulationTests(unittest.TestCase):
    def run_sim(self, cfg: SimConfig, seconds: float, key: str) -> Simulation:
        sim = Simulation(cfg, create_strategy(key))
        dt = 0.05
        steps = int(seconds / dt)
        for _ in range(steps):
            sim.step(dt)
        return sim

    def test_all_passengers_served(self) -> None:
        cfg = make_config(arrival_rate=6.0)
        sim = self.run_sim(cfg, 120.0, "algo.median")
        self.assertGreater(sim.metrics.served, 10)
        self.assertLessEqual(sim.waiting_count(), 2)
        riding = sum(len(e.passengers) for e in sim.elevators)
        self.assertEqual(
            sim.metrics.arrived,
            sim.metrics.served + sim.waiting_count() + riding,
        )

    def test_boarding_recorded(self) -> None:
        sim = self.run_sim(make_config(), 90.0, "algo.lobby")
        self.assertGreaterEqual(sim.metrics.boarded, sim.metrics.arrived - 2)
        self.assertGreater(sim.metrics.awt, 0.0)
        self.assertGreater(sim.metrics.travel_floors, 0.0)

    def test_passengers_reach_destination(self) -> None:
        sim = self.run_sim(make_config(floors=5), 60.0, "algo.stay")
        for floor_list in sim.waiting.values():
            for p in floor_list:
                self.assertIn(p.state, (PassengerState.WAITING, PassengerState.RIDING))
        self.assertGreater(sim.metrics.served, 0)

    def test_all_strategies_run(self) -> None:
        for key in REGISTRY:
            sim = self.run_sim(make_config(), 45.0, key)
            self.assertGreater(sim.metrics.served, 0, msg=key)

    def test_parked_elevator_returns_to_target(self) -> None:
        cfg = make_config(arrival_rate=0.0, idle_park_delay=0.5)
        sim = Simulation(cfg, create_strategy("algo.lobby"))
        for _ in range(200):
            sim.step(0.05)
        self.assertEqual(int(round(sim.elevators[0].floor)), 1)

    def test_custom_weights_parse(self) -> None:
        cfg = make_config(
            origin_mode="custom",
            custom_origin_weights="0,0,1,0,0,0,0,0",
        )
        gen = PassengerGenerator(cfg)
        events = gen.pop_until(600.0)
        self.assertTrue(events)
        self.assertTrue(all(e.origin == 3 for e in events))


if __name__ == "__main__":
    unittest.main()
