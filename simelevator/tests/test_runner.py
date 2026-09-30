from __future__ import annotations

import unittest

from core.models import ElevatorPhase, SimConfig
from core.profiles import RESIDENT, PassengerProfile, ProfileStore, TripLeg
from runner import (
    IDLE_MAX_STEP,
    MAX_FLOORS_PER_FRAME,
    MAX_IDLE_SCALE,
    ComparisonRunner,
)


class ComparisonRunnerTests(unittest.TestCase):
    def make_config(self) -> SimConfig:
        return SimConfig(
            floors=6,
            elevators=2,
            arrival_rate=10.0,
            seed=11,
            speed=2.0,
            door_time=0.5,
            boarding_time=0.4,
            alighting_time=0.3,
            min_door_open=0.5,
        )

    def test_shared_seed_identical_arrivals(self) -> None:
        runner = ComparisonRunner()
        runner.configure(
            self.make_config(), ["algo.stay", "algo.lobby", "algo.median"]
        )
        for _ in range(4000):
            runner.step(0.05)
        arrivals = [
            sim.metrics.arrived for sim in runner.sims.values()
        ]
        self.assertEqual(len(set(arrivals)), 1)
        self.assertGreater(arrivals[0], 10)

    def test_results_per_algorithm(self) -> None:
        runner = ComparisonRunner()
        keys = ["algo.lobby", "algo.zoned"]
        runner.configure(self.make_config(), keys)
        for _ in range(2000):
            runner.step(0.05)
        results = runner.results()
        self.assertEqual(set(results), set(keys))
        for snap in results.values():
            self.assertGreater(snap["served"], 0)

    def test_reconfigure_same_ignored(self) -> None:
        runner = ComparisonRunner()
        cfg = self.make_config()
        runner.configure(cfg, ["algo.lobby"])
        first = runner.sims["algo.lobby"]
        runner.configure(self.make_config(), ["algo.lobby"])
        self.assertIs(runner.sims["algo.lobby"], first)

    def test_reconfigure_changes_reset(self) -> None:
        runner = ComparisonRunner()
        runner.configure(self.make_config(), ["algo.lobby"])
        for _ in range(500):
            runner.step(0.05)
        runner.configure(self.make_config(), ["algo.lobby", "algo.median"])
        self.assertEqual(set(runner.sims), {"algo.lobby", "algo.median"})
        for sim in runner.sims.values():
            self.assertEqual(sim.now, 0.0)


class StepAutoTests(unittest.TestCase):
    """自适应时间步进：忙时平滑、空闲时快进且不跳过乘客事件。"""

    def make_config(self, **kw) -> SimConfig:
        base = dict(
            floors=20,
            elevators=2,
            speed=2.0,
            door_time=0.5,
            boarding_time=0.4,
            alighting_time=0.3,
            min_door_open=0.5,
            seed=3,
            passenger_source="profile",
            start_time_min=0,
            arrival_rate=0.0,
        )
        base.update(kw)
        return SimConfig(**base)

    @staticmethod
    def resident(home: int, target: int, at: int, stay: int = 600) -> PassengerProfile:
        # 显式给出抖动/出勤，否则 resolve 会随机填入导致事件被丢在负时间
        return PassengerProfile(
            pid=f"R{home}",
            name=f"r{home}",
            kind=RESIDENT,
            home_floor=home,
            legs=[TripLeg(time_min=at, target_floor=target, stay_min=stay)],
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=600.0,
        )

    def make_runner(self, profiles: list[PassengerProfile], **kw) -> ComparisonRunner:
        runner = ComparisonRunner()
        runner.configure(self.make_config(**kw), ["algo.median"], profiles)
        return runner

    def make_busy_runner(self, **kw) -> ComparisonRunner:
        """跑到 00:00 出行那一刻之后的状态：楼里已经有人等梯。"""
        runner = self.make_runner([self.resident(18, 1, 0, stay=120)], **kw)
        runner.step(0.1)
        self.assertTrue(runner.is_busy())
        return runner

    def test_step_auto_is_smooth_when_busy(self) -> None:
        # 00:00 出门，00:02 返程：整段都有乘客在等或在梯里
        runner = self.make_busy_runner()
        sim = runner.sims["algo.median"]
        max_jump = 0.0
        frames = 0
        while runner.is_busy() and frames < 60 * 60:
            before = [e.floor for e in sim.elevators]
            runner.step_auto(1 / 60, 1.0)
            after = [e.floor for e in sim.elevators]
            max_jump = max(max_jump, max(abs(a - b) for a, b in zip(before, after)))
            frames += 1
        self.assertGreater(frames, 100, msg="忙状态持续时间过短，测不出平滑效果")
        self.assertLessEqual(max_jump, MAX_FLOORS_PER_FRAME + 1e-6)

    def test_low_fps_does_not_teleport(self) -> None:
        runner = self.make_busy_runner()
        sim = runner.sims["algo.median"]
        before = [e.floor for e in sim.elevators]
        runner.step_auto(0.1, 10.0)  # 最坏的一帧
        after = [e.floor for e in sim.elevators]
        for a, b in zip(before, after):
            self.assertLessEqual(abs(a - b), MAX_FLOORS_PER_FRAME + 1e-6)

    def test_step_auto_fast_forwards_when_idle(self) -> None:
        runner = self.make_runner([self.resident(18, 1, 12 * 60)])
        stepped = runner.step_auto(1 / 60, 1.0)
        self.assertFalse(runner.is_busy())
        self.assertAlmostEqual(stepped, IDLE_MAX_STEP, places=6)
        self.assertAlmostEqual(stepped / (1 / 60), MAX_IDLE_SCALE, places=3)

    def test_idle_step_never_skips_the_next_event(self) -> None:
        # 00:02 出门：先闲置快进，再验证停步正好落在事件时刻
        runner = self.make_runner([self.resident(18, 1, 2, stay=30)])
        for _ in range(120):
            if runner.is_busy():
                break
            before = runner.now
            runner.step_auto(1 / 60, 1.0)
            self.assertLessEqual(runner.now, runner.next_demand_time() + 1e-6)
            self.assertGreater(runner.now, before)
        # 乘客正好在 now 出现，不会被快进跨过去
        self.assertTrue(runner.is_busy())
        self.assertAlmostEqual(runner.now, 2 * 60, delta=2.0)

    def test_idle_scale_is_bounded_at_high_frame_rate(self) -> None:
        runner = self.make_runner([self.resident(18, 1, 12 * 60)])
        stepped = runner.step_auto(0.001, 1.0)
        self.assertLessEqual(stepped / 0.001, MAX_IDLE_SCALE + 1e-6)

    def test_empty_parking_is_not_busy(self) -> None:
        runner = self.make_runner([self.resident(18, 1, 12 * 60)])
        runner.step_auto(1 / 60, 1.0)
        sim = runner.sims["algo.median"]
        for e in sim.elevators:
            e.phase = ElevatorPhase.MOVING
            e.direction = -1
            e.park_target = 1
            e.calls.clear()
            e.pickups.clear()
        self.assertFalse(runner.is_busy())
        for e in sim.elevators:
            e.phase = ElevatorPhase.OPEN
        self.assertTrue(runner.is_busy())

    def test_loaded_elevator_is_busy(self) -> None:
        runner = self.make_runner([self.resident(18, 1, 12 * 60)])
        runner.step_auto(1 / 60, 1.0)
        sim = runner.sims["algo.median"]
        sim.elevators[0].pickups.add((3, 1))
        self.assertTrue(runner.is_busy())

    def test_waiting_passenger_is_busy(self) -> None:
        self.assertTrue(self.make_busy_runner().is_busy())

    def test_next_demand_time_infinite_without_profiles(self) -> None:
        runner = self.make_runner([])
        self.assertEqual(runner.next_demand_time(), float("inf"))
        # 无画像时仍应快进，而不是卡死
        self.assertGreater(runner.step_auto(1 / 60, 1.0), 0.0)

    def test_step_auto_ignores_nonpositive_dt(self) -> None:
        runner = self.make_busy_runner()
        before = runner.now
        self.assertEqual(runner.step_auto(0.0, 10.0), 0.0)
        self.assertEqual(runner.step_auto(-1.0, 10.0), 0.0)
        self.assertEqual(runner.now, before)

    def test_step_auto_zero_scale_stops_when_busy(self) -> None:
        runner = self.make_busy_runner()
        self.assertEqual(runner.step_auto(1 / 60, 0.0), 0.0)
        self.assertAlmostEqual(runner.now, 0.1, places=6)

    def test_all_algorithms_step_together(self) -> None:
        runner = ComparisonRunner()
        runner.configure(
            self.make_config(), ["algo.lobby", "algo.median", "algo.stay"],
            [self.resident(18, 1, 0, stay=120)],
        )
        for _ in range(600):
            runner.step_auto(1 / 60, 1.0)
        times = {round(sim.now, 6) for sim in runner.sims.values()}
        self.assertEqual(len(times), 1)

    def test_profile_generator_next_time_matches_pop(self) -> None:
        runner = self.make_runner([self.resident(18, 1, 0, stay=120)])
        gen = runner.sims["algo.median"].generator
        for _ in range(60):
            nxt = gen.next_time(runner.now)
            self.assertGreaterEqual(nxt, runner.now - 1e-9)
            runner.step_auto(1 / 60, 1.0)
        # next_time 报出的时刻最终都会被 pop_until 触发，不漏不重
        pending = [e.time for e in gen.pop_until(runner.now + 1e-6)]
        self.assertTrue(all(t <= runner.now + 1e-6 for t in pending))
        self.assertGreaterEqual(gen.next_time(runner.now), runner.now)


if __name__ == "__main__":
    unittest.main()
