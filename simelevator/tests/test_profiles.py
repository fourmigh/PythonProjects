from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.building import (
    BUILDING_PRESETS,
    CHILD,
    DEFAULT_BUILDING,
    FEMALE,
    LOBBY_FLOOR,
    MALE,
    OFFICE,
    OFFICE_MIX,
    PEOPLE_KINDS,
    POPULATION_WARN,
    RESIDENTIAL,
    WHEELCHAIR,
    Building,
    Population,
    resident_template,
    visitor_template,
)
from core.models import SimConfig
from core.passenger import PassengerGenerator, _random_gender
from core.profile_generator import ProfileGenerator
from core.profiles import (
    PALETTE,
    RESIDENT,
    VISITOR,
    PassengerProfile,
    ProfileStore,
    TripLeg,
    derive_color,
    derive_gender,
    fill_defaults,
    is_people_kind,
    make_batch,
    needs_fill,
    resolve,
    sample_profiles,
    standard_schedule,
)
from core.simulator import Simulation
from algorithms import create_strategy


def cfg(**kw) -> SimConfig:
    base = dict(
        floors=8,
        elevators=2,
        speed=2.0,
        door_time=0.5,
        boarding_time=0.4,
        alighting_time=0.3,
        min_door_open=0.5,
        seed=7,
        passenger_source="profile",
    )
    base.update(kw)
    return SimConfig(**base)


class ResolveTests(unittest.TestCase):
    def test_resolve_fills_scalars(self) -> None:
        p = PassengerProfile(pid="P001", name="测试", kind=RESIDENT)
        r = resolve(p, floors=10, base_seed=1)
        self.assertIsNotNone(r.home_floor)
        self.assertIsNotNone(r.attendance)
        self.assertIsNotNone(r.jitter_min)
        self.assertIsNotNone(r.companions)
        self.assertIsNotNone(r.abandon_sec)
        self.assertTrue(r.weekdays)

    def test_resolve_does_not_invent_schedule(self) -> None:
        p = PassengerProfile(pid="P002", name="无日程", kind=RESIDENT)
        r = resolve(p, floors=10, base_seed=1)
        self.assertEqual(r.legs, [])
        self.assertIsNone(r.main_floor)

    def test_resolve_ignores_seed_and_floors(self) -> None:
        """归一化不是随机化：换种子/楼层数不得改变空字段的兜底值。"""
        p = PassengerProfile(pid="P002b", name="无日程", kind=RESIDENT)
        a = resolve(p, floors=10, base_seed=1)
        b = resolve(p, floors=24, base_seed=999)
        self.assertEqual(a.to_json(), b.to_json())

    def test_resolve_of_bare_profile_is_stable(self) -> None:
        p = PassengerProfile(pid="P002c", name="裸", kind=VISITOR)
        a = resolve(p, floors=8, base_seed=3)
        b = resolve(p, floors=8, base_seed=77)
        self.assertEqual(a.to_json(), b.to_json())

    def test_resolve_clears_resident_main_floor(self) -> None:
        p = PassengerProfile(pid="P003", name="旧数据", kind=RESIDENT, main_floor=5)
        r = resolve(p, floors=10, base_seed=1)
        self.assertIsNone(r.main_floor)

    def test_deterministic_same_seed(self) -> None:
        p = PassengerProfile(pid="P009", name="重复", kind=RESIDENT)
        a = fill_defaults(p, floors=8, base_seed=42)
        b = fill_defaults(p, floors=8, base_seed=42)
        self.assertEqual(a.to_json(), b.to_json())

    def test_different_seed_differs(self) -> None:
        p = PassengerProfile(pid="P010", name="变", kind=RESIDENT)
        a = fill_defaults(p, floors=20, base_seed=1)
        b = fill_defaults(p, floors=20, base_seed=2)
        self.assertNotEqual(
            (a.home_floor, a.jitter_min, a.companions),
            (b.home_floor, b.jitter_min, b.companions),
        )

    def test_floors_within_range(self) -> None:
        p = PassengerProfile(pid="P011", name="范围", kind=VISITOR)
        r = resolve(p, floors=5, base_seed=3)
        self.assertIn(r.main_floor, range(2, 6))
        self.assertGreaterEqual(r.visitor_stay, 1)

    def test_resident_leg_target_never_home(self) -> None:
        for seed in range(15):
            p = PassengerProfile(
                pid="P012",
                name="错层",
                kind=RESIDENT,
                legs=[TripLeg(time_min=8 * 60)],
            )
            r = fill_defaults(p, floors=6, base_seed=seed)
            self.assertNotEqual(r.legs[0].target_floor, r.home_floor, msg=f"seed={seed}")

    def test_visitor_defaults(self) -> None:
        p = PassengerProfile(pid="P013", name="访", kind=VISITOR)
        r = resolve(p, floors=10, base_seed=5)
        self.assertIsNotNone(r.visitor_arrive)
        self.assertIsNotNone(r.visitor_stay)


class FillDefaultsTests(unittest.TestCase):
    def test_resident_gets_standard_schedule(self) -> None:
        p = PassengerProfile(pid="F001", name="空日程", kind=RESIDENT)
        f = fill_defaults(p, floors=12, base_seed=3)
        self.assertTrue(f.legs)
        leg = f.legs[0]
        self.assertGreaterEqual(leg.time_min, 7 * 60)
        self.assertLessEqual(leg.time_min, 9 * 60)
        self.assertGreaterEqual(leg.stay_min, 8 * 60)
        self.assertLessEqual(leg.stay_min, 11 * 60)
        self.assertNotEqual(leg.target_floor, f.home_floor)

    def test_fill_is_complete(self) -> None:
        p = PassengerProfile(pid="F002", name="空", kind=RESIDENT)
        f = fill_defaults(p, floors=10, base_seed=1)
        self.assertFalse(needs_fill(f))

    def test_fill_idempotent(self) -> None:
        p = PassengerProfile(pid="F003", name="幂等", kind=RESIDENT)
        once = fill_defaults(p, floors=10, base_seed=2)
        twice = fill_defaults(once, floors=10, base_seed=2)
        self.assertEqual(once.to_json(), twice.to_json())

    def test_fill_deterministic(self) -> None:
        mk = lambda: PassengerProfile(pid="F004", name="确定", kind=RESIDENT)
        a = fill_defaults(mk(), floors=10, base_seed=7)
        b = fill_defaults(mk(), floors=10, base_seed=7)
        self.assertEqual(a.to_json(), b.to_json())

    def test_fill_preserves_existing_schedule(self) -> None:
        p = PassengerProfile(
            pid="F005",
            name="已有",
            kind=RESIDENT,
            home_floor=9,
            legs=[TripLeg(time_min=6 * 60, target_floor=1, stay_min=30)],
        )
        f = fill_defaults(p, floors=12, base_seed=1)
        self.assertEqual(len(f.legs), 1)
        self.assertEqual(f.legs[0].time_min, 6 * 60)

    def test_visitor_fill(self) -> None:
        p = PassengerProfile(pid="F006", name="访", kind=VISITOR)
        f = fill_defaults(p, floors=10, base_seed=4)
        self.assertFalse(needs_fill(f))
        self.assertIsNotNone(f.main_floor)
        self.assertIsNotNone(f.visitor_arrive)

    def test_standard_schedule_range(self) -> None:
        for seed in range(30):
            legs = standard_schedule(5, 2, seed, f"P{seed:03d}", "n")
            self.assertEqual(len(legs), 1)
            self.assertGreaterEqual(legs[0].time_min, 7 * 60)
            self.assertLessEqual(legs[0].time_min, 9 * 60)


class ProfileGeneratorTests(unittest.TestCase):
    def test_resident_morning_and_evening(self) -> None:
        p = PassengerProfile(
            pid="P100",
            name="早出晚归",
            kind=RESIDENT,
            home_floor=8,
            main_floor=2,
            legs=[TripLeg(time_min=8 * 60, target_floor=2, stay_min=600)],
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=600,
        )
        gen = ProfileGenerator(cfg(start_time_min=6 * 60), [p])
        events = gen.pop_until(24 * 3600)
        # 8->2 (morning) and 2->8 (evening) = 2 trips
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].origin, 8)
        self.assertEqual(events[0].dest, 2)
        self.assertEqual(events[1].origin, 2)
        self.assertEqual(events[1].dest, 8)

    def test_companions_multiply_events(self) -> None:
        p = PassengerProfile(
            pid="P101",
            name="结伴",
            kind=RESIDENT,
            home_floor=5,
            main_floor=3,
            legs=[TripLeg(time_min=9 * 60, target_floor=3, stay_min=60)],
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=3,
            abandon_sec=600,
        )
        gen = ProfileGenerator(cfg(start_time_min=6 * 60), [p])
        events = gen.pop_until(24 * 3600)
        morning = [e for e in events if e.origin == 5]
        self.assertEqual(len(morning), 3)
        self.assertEqual(len({e.time for e in morning}), 1)

    def test_visitor_round_trip_from_lobby(self) -> None:
        p = PassengerProfile(
            pid="P102",
            name="访客",
            kind=VISITOR,
            main_floor=7,
            visitor_arrive=10 * 60,
            visitor_stay=60,
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=600,
        )
        gen = ProfileGenerator(cfg(start_time_min=6 * 60), [p])
        events = gen.pop_until(24 * 3600)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].origin, 1)
        self.assertEqual(events[0].dest, 7)
        self.assertEqual(events[1].origin, 7)
        self.assertEqual(events[1].dest, 1)

    def test_daily_repeat_next_day(self) -> None:
        p = PassengerProfile(
            pid="P103",
            name="每天",
            kind=RESIDENT,
            home_floor=4,
            main_floor=2,
            legs=[TripLeg(time_min=8 * 60, target_floor=2, stay_min=30)],
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=600,
        )
        gen = ProfileGenerator(cfg(start_time_min=0), [p])
        day1 = gen.pop_until(1 * 86400)
        day2 = gen.pop_until(2 * 86400)
        self.assertEqual(len(day1), 2)
        self.assertEqual(len(day2), 2)
        self.assertTrue(all(e.time >= 86400 for e in day2))

    def test_start_time_shifts_events(self) -> None:
        p = PassengerProfile(
            pid="P104",
            name="偏移",
            kind=RESIDENT,
            home_floor=6,
            main_floor=2,
            legs=[TripLeg(time_min=9 * 60, target_floor=2, stay_min=30)],
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=600,
        )
        # start at 06:00, 09:00 event -> 3h -> 10800s
        gen = ProfileGenerator(cfg(start_time_min=6 * 60), [p])
        events = gen.pop_until(6 * 3600)
        self.assertTrue(events)
        self.assertAlmostEqual(events[0].time, 3 * 3600, delta=2)

    def test_need_meet_delays_visitor(self) -> None:
        base = dict(
            pid="P105",
            name="等人",
            kind=VISITOR,
            main_floor=5,
            visitor_stay=30,
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=600,
        )
        without = ProfileGenerator(
            cfg(start_time_min=6 * 60),
            [PassengerProfile(**base, visitor_arrive=9 * 60, needs_meet=False)],
        ).pop_until(6 * 3600)
        with_meet = ProfileGenerator(
            cfg(start_time_min=6 * 60),
            [PassengerProfile(**base, visitor_arrive=9 * 60, needs_meet=True)],
        ).pop_until(6 * 3600)
        self.assertEqual(with_meet[0].time - without[0].time, 5 * 60)

    def test_identical_event_stream_same_config(self) -> None:
        profiles = sample_profiles()
        g1 = ProfileGenerator(cfg(), profiles)
        g2 = ProfileGenerator(cfg(), profiles)
        e1 = g1.pop_until(12 * 3600)
        e2 = g2.pop_until(12 * 3600)
        self.assertEqual(
            [(e.pid, e.origin, e.dest, round(e.time, 3)) for e in e1],
            [(e.pid, e.origin, e.dest, round(e.time, 3)) for e in e2],
        )

    def test_legless_resident_never_travels(self) -> None:
        p = PassengerProfile(
            pid="P106",
            name="从不出行",
            kind=RESIDENT,
            home_floor=5,
            color=PALETTE[0],
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=600,
        )
        self.assertEqual(p.legs, [])
        gen = ProfileGenerator(cfg(start_time_min=0), [p])
        self.assertEqual(gen.pop_until(2 * 86400), [])

    def test_changing_seed_does_not_re_roll_legless(self) -> None:
        p = PassengerProfile(
            pid="P107",
            name="冻结",
            kind=RESIDENT,
            home_floor=4,
            color=PALETTE[1],
            legs=[TripLeg(time_min=8 * 60, target_floor=2, stay_min=600)],
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=600,
        )
        a = ProfileGenerator(cfg(start_time_min=0, seed=1), [p]).pop_until(86400)
        b = ProfileGenerator(cfg(start_time_min=0, seed=999), [p]).pop_until(86400)
        self.assertEqual(
            [(e.origin, e.dest, round(e.time)) for e in a],
            [(e.origin, e.dest, round(e.time)) for e in b],
        )


class AbandonTests(unittest.TestCase):
    def test_passenger_gives_up_after_deadline(self) -> None:
        p = PassengerProfile(
            pid="P200",
            name="急",
            kind=RESIDENT,
            home_floor=8,
            main_floor=2,
            legs=[TripLeg(time_min=8 * 60, target_floor=2, stay_min=30)],
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=10.0,
        )
        # one very slow elevator so hall calls are slow; allow abandon
        config = cfg(
            start_time_min=6 * 60,
            speed=0.2,
            allow_abandon=True,
        )
        sim = Simulation(config, create_strategy("algo.lobby"), generator=ProfileGenerator(config, [p]))
        dt = 0.5
        for _ in range(int(3 * 3600 / dt)):
            sim.step(dt)
        self.assertGreaterEqual(sim.metrics.abandoned, 1)

    def test_abandon_disabled_keeps_all(self) -> None:
        p = PassengerProfile(
            pid="P201",
            name="不弃",
            kind=RESIDENT,
            home_floor=8,
            main_floor=2,
            legs=[TripLeg(time_min=8 * 60, target_floor=2, stay_min=30)],
            weekdays=[1, 2, 3, 4, 5, 6, 7],
            attendance=1.0,
            jitter_min=0,
            companions=1,
            abandon_sec=10.0,
        )
        config = cfg(start_time_min=6 * 60, speed=0.2, allow_abandon=False)
        sim = Simulation(config, create_strategy("algo.lobby"), generator=ProfileGenerator(config, [p]))
        dt = 0.5
        for _ in range(int(2 * 3600 / dt)):
            sim.step(dt)
        self.assertEqual(sim.metrics.abandoned, 0)


class ProfileStoreTests(unittest.TestCase):
    def test_json_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            store = ProfileStore(path)
            store.save(sample_profiles())
            loaded = ProfileStore(path).load()
            self.assertEqual(len(loaded), len(sample_profiles()))
            self.assertEqual(loaded[0].name, sample_profiles()[0].name)
            self.assertEqual(loaded[0].legs[0].target_floor, sample_profiles()[0].legs[0].target_floor)

    def test_load_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProfileStore(Path(tmp) / "none.json")
            self.assertEqual(store.load(), [])

    def test_next_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProfileStore(Path(tmp) / "p.json")
            store.save(sample_profiles())
            self.assertEqual(store.next_index(), 10)

    def test_batch_generation(self) -> None:
        floors = 8
        population = DEFAULT_BUILDING.population(floors, 1)
        batch = make_batch(start_index=1, base_seed=1, floors=floors, floor_mode="uniform")
        self.assertEqual(len(batch), population.total)
        for p in batch:
            if p.kind == RESIDENT:
                self.assertIsNotNone(p.home_floor)
                self.assertIn(p.home_floor, range(2, 9))
                self.assertIsNone(p.main_floor)
                self.assertTrue(p.legs, msg=p.pid)

    def test_batch_is_complete(self) -> None:
        for building in (BUILDING_PRESETS[RESIDENTIAL], BUILDING_PRESETS[OFFICE]):
            batch = make_batch(
                start_index=1,
                base_seed=2,
                floors=10,
                building=building,
                population=building.population(10, 2),
            )
            for p in batch:
                self.assertFalse(needs_fill(p), msg=f"{building.kind} {p.pid}")

    def test_batch_low_mode_skews_to_low_floors(self) -> None:
        def low_share(mode: str) -> float:
            batch = make_batch(
                start_index=1,
                base_seed=5,
                floors=12,
                floor_mode=mode,
                population=DEFAULT_BUILDING.population(12, 5),
            )
            residents = [p for p in batch if p.kind == RESIDENT]
            return sum(1 for p in residents if p.home_floor <= 4) / len(residents)

        self.assertGreater(low_share("low"), low_share("uniform"))

    def test_batch_deterministic(self) -> None:
        a = make_batch(start_index=1, base_seed=9, floors=8)
        b = make_batch(start_index=1, base_seed=9, floors=8)
        self.assertEqual([p.to_json() for p in a], [p.to_json() for p in b])

    def test_batch_count_follows_building_capacity(self) -> None:
        """批量数量由大楼容量决定，而不是调用方指定。"""
        small = Building(RESIDENTIAL, 0.9, 1.0, 1, (2, 2))
        big = Building(RESIDENTIAL, 0.9, 1.0, 4, (2, 2))
        floors = 10
        n_small = len(make_batch(start_index=1, base_seed=4, floors=floors, building=small))
        n_big = len(make_batch(start_index=1, base_seed=4, floors=floors, building=big))
        self.assertEqual(n_small, small.population(floors, 4).total)
        self.assertEqual(n_big, big.population(floors, 4).total)
        # 单元数 ×4 → 住客 ×4，访客按同一占比放大
        self.assertEqual(n_big, n_small * 4)

    def test_batch_accepts_explicit_population(self) -> None:
        pop = DEFAULT_BUILDING.population(6, 1)
        batch = make_batch(start_index=1, base_seed=1, floors=6, population=pop)
        self.assertEqual(len(batch), pop.total)
        residents = sum(1 for p in batch if p.kind == RESIDENT)
        self.assertEqual(residents, pop.residents)

    def test_summary_key_no_hardcoded_text(self) -> None:
        r = fill_defaults(PassengerProfile(pid="S1", name="x", kind=RESIDENT), 8, 1)
        self.assertEqual(r.summary_key(), "profile.leg_count")
        v = resolve(PassengerProfile(pid="S2", name="y", kind=VISITOR), 8, 1)
        self.assertEqual(v.summary_key(), "profile.stay_min")
        empty = PassengerProfile(pid="S3", name="z", kind=RESIDENT)
        self.assertEqual(empty.summary_key(), "profile.no_legs")


class ColorTests(unittest.TestCase):
    def test_invalid_color_falls_back_deterministically(self) -> None:
        p = PassengerProfile(pid="C001", name="c", color="#not-a-color")
        a = resolve(p, floors=8, base_seed=1)
        b = resolve(p, floors=8, base_seed=1)
        self.assertEqual(a.color, b.color)
        self.assertIn(a.color, PALETTE)

    def test_derive_color_stable(self) -> None:
        self.assertEqual(derive_color("C001"), derive_color("C001"))
        self.assertIn(derive_color("C001"), PALETTE)


class ProfileSimulationTests(unittest.TestCase):
    def test_sample_profiles_run(self) -> None:
        config = cfg(start_time_min=6 * 60, arrival_rate=0.0)
        sim = Simulation(
            config,
            create_strategy("algo.median"),
            generator=ProfileGenerator(config, sample_profiles()),
        )
        dt = 0.1
        for _ in range(int(20 * 3600 / dt)):
            sim.step(dt)
        self.assertGreater(sim.metrics.served, 10)
        self.assertLessEqual(sim.waiting_count(), 3)

    def test_all_arrived_eventually_leave_lobby_or_ride(self) -> None:
        config = cfg(start_time_min=6 * 60)
        sim = Simulation(
            config,
            create_strategy("algo.lobby"),
            generator=ProfileGenerator(config, sample_profiles()),
        )
        dt = 0.1
        for _ in range(int(16 * 3600 / dt)):
            sim.step(dt)
        total = sim.metrics.arrived
        accounted = sim.metrics.served + sim.metrics.abandoned + sim.waiting_count()
        self.assertEqual(total, accounted)


class BuildingTests(unittest.TestCase):
    def _residents(self, count: int = 100, kind: str = RESIDENTIAL, floors: int = 8) -> list[PassengerProfile]:
        building = BUILDING_PRESETS[kind]
        population = building.population(floors, 42)
        if count != population.total:
            population = Population(
                population.units, population.occupied, count, 0
            )
        return [
            p
            for p in make_batch(1, 42, floors, building, population=population)
            if p.kind == RESIDENT
        ]

    def test_normalized_clamps_and_falls_back(self) -> None:
        self.assertEqual(Building("nonsense", 0.5).normalized().kind, RESIDENTIAL)
        self.assertEqual(Building(RESIDENTIAL, 1.5).normalized().resident_share, 1.0)
        self.assertEqual(Building(RESIDENTIAL, -1.0).normalized().resident_share, 0.0)
        self.assertEqual(Building(RESIDENTIAL, "bad").normalized().resident_share, 0.9)

    def test_normalized_clamps_capacity_fields(self) -> None:
        b = Building(RESIDENTIAL, 0.9, 1.8, 999, (9, 1)).normalized()
        self.assertEqual(b.occupancy_rate, 1.0)
        self.assertEqual(b.units_per_floor, 999)
        self.assertEqual(b.occupants_per_unit, (1, 9))
        b2 = Building(OFFICE, 0.2, -0.5, -3, (0, -7)).normalized()
        self.assertEqual(b2.occupancy_rate, 0.0)
        self.assertEqual(b2.units_per_floor, 0)
        self.assertEqual(b2.occupants_per_unit, (1, 1))

    def test_normalized_falls_back_per_field(self) -> None:
        bad = Building(OFFICE, "x", "y", "z", "w").normalized()
        preset = BUILDING_PRESETS[OFFICE]
        self.assertEqual(bad.occupancy_rate, preset.occupancy_rate)
        self.assertEqual(bad.units_per_floor, preset.units_per_floor)
        self.assertEqual(bad.occupants_per_unit, preset.occupants_per_unit)

    def test_presets(self) -> None:
        res, off = BUILDING_PRESETS[RESIDENTIAL], BUILDING_PRESETS[OFFICE]
        self.assertEqual(res.resident_share, 0.9)
        self.assertEqual(off.resident_share, 0.2)
        self.assertEqual((res.occupancy_rate, res.units_per_floor), (0.85, 4))
        self.assertEqual(res.occupants_per_unit, (2, 4))
        self.assertEqual((off.occupancy_rate, off.units_per_floor), (0.70, 2))
        self.assertEqual(off.occupants_per_unit, (8, 30))
        self.assertEqual(DEFAULT_BUILDING.kind, RESIDENTIAL)

    def test_office_units_hold_more_people_than_homes(self) -> None:
        """商务楼的「公司」比住宅的「户」人更多。"""
        res, off = BUILDING_PRESETS[RESIDENTIAL], BUILDING_PRESETS[OFFICE]
        self.assertGreater(off.occupants_per_unit[0], res.occupants_per_unit[1])

    def test_capacity_excludes_lobby(self) -> None:
        b = Building(RESIDENTIAL, 0.9, 1.0, 4, (2, 2))
        self.assertEqual(LOBBY_FLOOR, 1)
        self.assertEqual(b.capacity(1), 0)
        self.assertEqual(b.capacity(2), 4)
        self.assertEqual(b.capacity(10), 36)

    def test_population_math(self) -> None:
        b = Building(RESIDENTIAL, 0.9, 0.5, 4, (2, 2))
        pop = b.population(10, 1)
        self.assertEqual(pop.units, 36)
        self.assertEqual(pop.occupied, 18)  # round(36 * 0.5)
        self.assertEqual(pop.residents, 18 * 2)  # 固定每户 2 人
        self.assertEqual(pop.visitors, 4)  # round(36 * 0.1 / 0.9)
        self.assertEqual(pop.total, 40)

    def test_population_zero_without_units(self) -> None:
        pop = DEFAULT_BUILDING.population(1, 1)
        self.assertEqual((pop.units, pop.occupied, pop.residents, pop.total), (0, 0, 0, 0))

    def test_population_occupant_range_is_respected(self) -> None:
        b = Building(RESIDENTIAL, 0.9, 1.0, 3, (2, 4))
        pop = b.population(8, 7)
        self.assertEqual(pop.occupied, 21)
        self.assertGreaterEqual(pop.residents, 42)
        self.assertLessEqual(pop.residents, 84)

    def test_population_is_deterministic(self) -> None:
        b = BUILDING_PRESETS[OFFICE]
        self.assertEqual(b.population(20, 3), b.population(20, 3))
        self.assertNotEqual(b.population(20, 3), b.population(20, 4))
        self.assertNotEqual(b.population(20, 3), b.population(21, 3))

    def test_population_scales_with_every_capacity_field(self) -> None:
        base = Building(RESIDENTIAL, 0.9, 1.0, 1, (3, 3))
        more_units = Building(RESIDENTIAL, 0.9, 1.0, 2, (3, 3))
        more_people = Building(RESIDENTIAL, 0.9, 1.0, 1, (6, 6))
        self.assertEqual(
            more_units.population(10, 5).residents,
            2 * base.population(10, 5).residents,
        )
        self.assertEqual(
            more_people.population(10, 5).residents,
            2 * base.population(10, 5).residents,
        )
        # 入住率减半 → 已入驻单元减半 → 住客同步减半
        half = Building(RESIDENTIAL, 0.9, 0.5, 1, (3, 3)).population(10, 5)
        base_pop = base.population(10, 5)
        self.assertEqual(base_pop.occupied, 9)
        self.assertEqual(half.occupied, 4)  # round(9 * 0.5)
        self.assertEqual(half.residents, 12)
        self.assertLess(half.residents, base_pop.residents)
        # 住客占比只改访客数，不改住客数
        even_split = Building(RESIDENTIAL, 0.5, 1.0, 1, (3, 3)).population(10, 5)
        self.assertEqual(even_split.residents, base_pop.residents)
        self.assertEqual(even_split.visitors, even_split.residents)
        self.assertGreater(even_split.visitors, base_pop.visitors)

    def test_population_zero_share_yields_no_visitors(self) -> None:
        b = Building(RESIDENTIAL, 0.0, 1.0, 2, (2, 2))
        pop = b.population(6, 1)
        self.assertGreater(pop.residents, 0)
        self.assertEqual(pop.visitors, 0)
        self.assertEqual(pop.total, pop.residents)

    def test_residential_batch_split_follows_share(self) -> None:
        batch = make_batch(
            1,
            3,
            8,
            BUILDING_PRESETS[RESIDENTIAL],
            population=Population(100, 100, 180, 20),
        )
        self.assertEqual(len(batch), 200)
        share = sum(1 for p in batch if p.kind == RESIDENT) / len(batch)
        self.assertAlmostEqual(share, 0.9, delta=0.01)

    def test_office_batch_split_follows_share(self) -> None:
        batch = make_batch(
            1,
            3,
            8,
            BUILDING_PRESETS[OFFICE],
            population=Population(100, 100, 40, 160),
        )
        share = sum(1 for p in batch if p.kind == RESIDENT) / len(batch)
        self.assertAlmostEqual(share, 0.2, delta=0.01)

    def test_manual_share_is_respected(self) -> None:
        batch = make_batch(
            1,
            3,
            8,
            Building(OFFICE, 0.5),
            population=Population(100, 100, 50, 50),
        )
        share = sum(1 for p in batch if p.kind == RESIDENT) / len(batch)
        self.assertAlmostEqual(share, 0.5, delta=0.01)

    def test_residential_schedule_targets_lobby(self) -> None:
        for p in self._residents():
            self.assertGreaterEqual(p.home_floor, 2)
            self.assertEqual(p.legs[0].target_floor, 1)
            self.assertTrue(7 * 60 <= p.legs[0].time_min <= 9 * 60)

    def test_office_schedule_starts_at_lobby(self) -> None:
        for p in self._residents(kind=OFFICE):
            self.assertEqual(p.home_floor, 1)
            self.assertGreaterEqual(p.legs[0].target_floor, 2)
            self.assertTrue(8 * 60 <= p.legs[0].time_min <= 9 * 60 + 30)

    def test_templates_define_distinct_routines(self) -> None:
        res, off = BUILDING_PRESETS[RESIDENTIAL], BUILDING_PRESETS[OFFICE]
        self.assertEqual(resident_template(res).target, "lobby")
        self.assertEqual(resident_template(off).target, "office")
        self.assertEqual(visitor_template(res).meet_chance, 0.0)
        self.assertEqual(visitor_template(off).meet_chance, 0.6)
        self.assertEqual(visitor_template(off).companions, (1, 3))
        self.assertEqual(visitor_template(res).companions, (1, 4))

    def test_residential_peak_is_downward(self) -> None:
        self._assert_peak_direction(RESIDENTIAL, upward=False)

    def test_office_peak_is_upward(self) -> None:
        self._assert_peak_direction(OFFICE, upward=True)

    def _assert_peak_direction(self, kind: str, upward: bool) -> None:
        # 从零点起跑两天，只看第 0 天早高峰窗口的事件方向
        config = cfg(start_time_min=0, arrival_rate=0.0)
        building = BUILDING_PRESETS[kind]
        batch = make_batch(
            1,
            11,
            10,
            building,
            population=Population(100, 100, 108, 12),
        )
        events = ProfileGenerator(config, batch).pop_until(86400)
        morning = [e for e in events if 6.5 * 3600 <= e.time <= 9.5 * 3600]
        self.assertGreater(len(morning), 20, msg=kind)
        up = sum(1 for e in morning if e.dest > e.origin)
        down = len(morning) - up
        if upward:
            self.assertGreater(up, down * 2, msg=f"{kind}: up={up} down={down}")
        else:
            self.assertGreater(down, up * 2, msg=f"{kind}: up={up} down={down}")

    def test_office_visitors_often_need_meet(self) -> None:
        building = BUILDING_PRESETS[OFFICE]
        batch = make_batch(
            1,
            5,
            8,
            building,
            population=Population(100, 100, 40, 160),
        )
        visitors = [p for p in batch if p.kind == VISITOR]
        share = sum(1 for p in visitors if p.needs_meet) / len(visitors)
        self.assertGreater(share, 0.4)
        self.assertLess(share, 0.8)

    def test_residential_visitors_never_need_meet(self) -> None:
        building = BUILDING_PRESETS[RESIDENTIAL]
        batch = make_batch(
            1,
            5,
            8,
            building,
            population=Population(100, 100, 90, 10),
        )
        self.assertFalse(any(p.needs_meet for p in batch if p.kind == VISITOR))

    def test_fill_defaults_without_building_matches_residential(self) -> None:
        a = fill_defaults(PassengerProfile(pid="B1", name="x", kind=RESIDENT), 8, 4)
        b = fill_defaults(
            PassengerProfile(pid="B1", name="x", kind=RESIDENT),
            8,
            4,
            BUILDING_PRESETS[RESIDENTIAL],
        )
        self.assertEqual(a.to_json(), b.to_json())

    def test_building_json_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            store = ProfileStore(path)
            store.building = Building(OFFICE, 0.35, 0.55, 3, (12, 18))
            store.save(sample_profiles())
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["building"]["occupancy_rate"], 0.55)
            self.assertEqual(raw["building"]["units_per_floor"], 3)
            self.assertEqual(raw["building"]["occupants_per_unit"], [12, 18])
            reloaded = ProfileStore(path)
            reloaded.load()
            self.assertEqual(reloaded.profiles[0].name, "张伟")
            # 没给 people_mix 时按楼型回退，所以重载后拿到的是商务楼预设构成
            self.assertEqual(
                reloaded.building,
                Building(OFFICE, 0.35, 0.55, 3, (12, 18), dict(OFFICE_MIX)),
            )

    def test_old_json_without_building_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            payload = {"profiles": [p.to_json() for p in sample_profiles()]}
            path.write_text(json.dumps(payload), encoding="utf-8")
            store = ProfileStore(path)
            store.load()
            self.assertEqual(store.building, DEFAULT_BUILDING)
            self.assertEqual(len(store.profiles), len(sample_profiles()))

    def test_json_without_capacity_fields_uses_preset_defaults(self) -> None:
        """上一版 JSON 只有楼型与占比，容量字段必须回退到住宅楼预设。"""
        legacy = {"kind": "residential", "resident_share": 0.9}
        loaded = Building.from_json(legacy)
        self.assertEqual(loaded, DEFAULT_BUILDING)
        self.assertEqual(loaded.occupancy_rate, 0.85)
        self.assertEqual(loaded.units_per_floor, 4)
        self.assertEqual(loaded.occupants_per_unit, (2, 4))

    def test_json_capacity_fields_load_for_office(self) -> None:
        loaded = Building.from_json(
            {
                "kind": "office",
                "resident_share": 0.2,
                "occupancy_rate": 0.5,
                "units_per_floor": 2,
                "occupants_per_unit": [10, 12],
            }
        )
        # 人群构成与三个特殊参数缺键时按楼型预设回退
        self.assertEqual(
            loaded,
            Building(OFFICE, 0.2, 0.5, 2, (10, 12), dict(OFFICE_MIX)),
        )

    def test_corrupt_building_falls_back(self) -> None:
        self.assertEqual(Building.from_json(None), DEFAULT_BUILDING)
        self.assertEqual(Building.from_json("junk"), DEFAULT_BUILDING)
        self.assertEqual(Building.from_json({"kind": 3, "resident_share": "x"}), DEFAULT_BUILDING)
        self.assertEqual(
            Building.from_json({"kind": "office", "occupants_per_unit": "bad"}),
            BUILDING_PRESETS[OFFICE],
        )

    def test_population_warn_threshold_is_positive(self) -> None:
        self.assertGreater(POPULATION_WARN, 0)
        self.assertLess(POPULATION_WARN, DEFAULT_BUILDING.population(60, 1).total)

    def test_building_does_not_reroll_existing_profiles(self) -> None:
        existing = sample_profiles()
        before = [p.to_json() for p in existing]
        # 楼型只在创建时起作用：resolve() 完全不感知楼型
        after = [resolve(p, 24, 7).to_json() for p in existing]
        self.assertEqual(before, after)


class PeopleMixTests(unittest.TestCase):
    """人群构成：四类占比、精确人数分配与归一化。"""

    def test_mix_presets_sum_to_one(self) -> None:
        for kind in (RESIDENTIAL, OFFICE):
            mix = BUILDING_PRESETS[kind].normalized().people_mix
            self.assertEqual(set(mix), set(PEOPLE_KINDS))
            self.assertAlmostEqual(sum(mix.values()), 1.0, places=6)

    def test_mix_for_falls_back_to_preset(self) -> None:
        # 直接构造、且没给 people_mix 时，混排必须按楼型回退，
        # 不能沿用住宅预设
        bare = Building(OFFICE, 0.2, 0.5, 1, (2, 2))
        for kind in PEOPLE_KINDS:
            self.assertAlmostEqual(
                bare.mix_for(kind), BUILDING_PRESETS[OFFICE].mix_for(kind)
            )

    def test_mix_normalized_scales_to_one(self) -> None:
        b = Building(RESIDENTIAL, 0.9, 0.85, 1, (2, 2), people_mix={"male": 50, "female": 30})
        mix = b.normalized().people_mix
        self.assertAlmostEqual(sum(mix.values()), 1.0, places=3)
        # 归一化会四舍五入到 4 位，比值只能给到 delta 级别
        self.assertAlmostEqual(mix[MALE] / mix[FEMALE], 50 / 30, delta=1e-3)

    def test_mix_normalized_handles_all_zero(self) -> None:
        b = Building(RESIDENTIAL, 0.9, 0.85, 1, (2, 2), people_mix=dict.fromkeys(PEOPLE_KINDS, 0))
        self.assertAlmostEqual(sum(b.normalized().people_mix.values()), 1.0, places=3)

    def test_partial_mix_falls_back_per_category(self) -> None:
        # 只写两类时，另外两类按楼型预设补，而不是当成 0
        b = Building(RESIDENTIAL, 0.9, 0.85, 1, (2, 2), people_mix={MALE: 0.9, FEMALE: 0.1})
        mix = b.normalized().people_mix
        self.assertEqual(set(mix), set(PEOPLE_KINDS))
        for kind in PEOPLE_KINDS:
            self.assertGreater(mix[kind], 0.0)

    def test_category_counts_match_total_exactly(self) -> None:
        # 最大余数法：不管占比多零碎，四类人数之和必须精确等于总数
        b = Building(RESIDENTIAL, 0.9, 0.85, 1, (2, 2))
        for total in (0, 1, 2, 7, 99, 1000, 2570):
            counts = b.category_counts(total)
            self.assertEqual(sum(counts.values()), total, msg=f"total={total}")
            for cat in PEOPLE_KINDS:
                self.assertGreaterEqual(counts[cat], 0)

    def test_category_counts_follow_mix(self) -> None:
        b = Building(
            RESIDENTIAL, 0.9, 0.85, 1, (2, 2),
            people_mix={MALE: 0.5, FEMALE: 0.5, CHILD: 0.0, WHEELCHAIR: 0.0},
        )
        counts = b.category_counts(100)
        self.assertEqual(counts[MALE], 50)
        self.assertEqual(counts[FEMALE], 50)
        self.assertEqual(counts[CHILD], 0)
        self.assertEqual(counts[WHEELCHAIR], 0)

    def test_people_mix_keeps_building_hashable(self) -> None:
        # dict 字段必须排除在 __hash__ 之外，否则 frozen dataclass 会
        # 抛 TypeError，runner 拿楼栋当缓存 key 时就炸了
        self.assertIsInstance(hash(Building(RESIDENTIAL)), int)

    def test_people_mix_json_round_trip(self) -> None:
        b = Building(
            RESIDENTIAL, 0.9, 0.85, 2, (2, 4),
            people_mix={"male": 0.3, "female": 0.3, "child": 0.3, "wheelchair": 0.1},
            wheelchair_patience=2.5,
            child_min_companions=4,
            child_patience=0.25,
        )
        self.assertEqual(Building.from_json(b.to_json()), b)

    def test_legacy_json_without_people_fields_falls_back(self) -> None:
        # 旧存档里没有 people_mix 和三个特殊参数，必须按楼型预设补齐
        loaded = Building.from_json({"kind": RESIDENTIAL})
        preset = BUILDING_PRESETS[RESIDENTIAL]
        self.assertEqual(loaded.people_mix, preset.people_mix)
        self.assertEqual(loaded.wheelchair_patience, preset.wheelchair_patience)
        self.assertEqual(loaded.child_min_companions, preset.child_min_companions)
        self.assertEqual(loaded.child_patience, preset.child_patience)


class CategoryBehaviorTests(unittest.TestCase):
    """儿童 / 轮椅的特殊行为，以及人群分类的确定性。"""

    def only(self, kind: str, **kw) -> Building:
        """一个只产出指定人群的小楼，capacity 由 kw 覆盖。"""
        base = dict(
            kind=RESIDENTIAL, resident_share=1.0, occupancy_rate=1.0,
            units_per_floor=1, occupants_per_unit=(2, 2),
        )
        base.update(kw)
        mix = dict.fromkeys(PEOPLE_KINDS, 0.0)
        mix[kind] = 1.0
        return Building(people_mix=mix, **base)

    def test_derive_gender_is_deterministic(self) -> None:
        self.assertEqual(derive_gender("P001"), derive_gender("P001"))
        self.assertIn(derive_gender("P001"), PEOPLE_KINDS)

    def test_is_people_kind_rejects_unknown(self) -> None:
        self.assertFalse(is_people_kind("dog"))
        for kind in PEOPLE_KINDS:
            self.assertTrue(is_people_kind(kind))

    def test_fill_defaults_repairs_missing_gender(self) -> None:
        p = PassengerProfile(pid="P1", name="测试", kind=RESIDENT)
        self.assertFalse(is_people_kind(p.gender))
        filled = fill_defaults(p, 8, 7, BUILDING_PRESETS[RESIDENTIAL])
        self.assertIn(filled.gender, PEOPLE_KINDS)

    def test_resolve_keeps_existing_gender(self) -> None:
        # resolve 会补齐作息等空字段，但绝不该改写已经填好的分类
        p = PassengerProfile(pid="P1", name="测试", kind=RESIDENT, gender=WHEELCHAIR)
        self.assertEqual(resolve(p, 24, 7).gender, WHEELCHAIR)

    def test_child_gets_companions_and_lower_patience(self) -> None:
        b = self.only(CHILD, child_min_companions=3, child_patience=0.5)
        profiles = make_batch(0, 7, 8, b)
        self.assertTrue(profiles)
        for p in profiles:
            self.assertEqual(p.gender, CHILD)
            self.assertGreaterEqual(p.companions, b.child_min_companions)

    def test_child_patience_shortens_deadline(self) -> None:
        base = self.only(MALE)
        child = self.only(CHILD, child_patience=0.5)
        avg = lambda b: sum(p.abandon_sec for p in make_batch(0, 7, 8, b)) / len(
            make_batch(0, 7, 8, b)
        )
        self.assertLess(avg(child), avg(base))

    def test_wheelchair_waits_longer_and_travels_alone(self) -> None:
        b = self.only(WHEELCHAIR)
        for p in make_batch(0, 7, 8, b):
            self.assertEqual(p.gender, WHEELCHAIR)
            # 轮椅默认固定 1 人同行，不再乘伴乘效应
            self.assertEqual(p.companions, 1)

    def test_wheelchair_patience_scales_deadline(self) -> None:
        quick = self.only(WHEELCHAIR, wheelchair_patience=1.0)
        patient = self.only(WHEELCHAIR, wheelchair_patience=5.0)
        avg = lambda b: sum(p.abandon_sec for p in make_batch(0, 7, 8, b)) / len(
            make_batch(0, 7, 8, b)
        )
        self.assertGreater(avg(patient), avg(quick))

    def test_special_behavior_is_not_reapplied(self) -> None:
        # 已有 companions / abandon_sec 的画像不能被二次改写
        b = self.only(CHILD, child_min_companions=5, child_patience=0.1)
        p = PassengerProfile(
            pid="P1", name="测试", kind=RESIDENT, gender=CHILD,
            companions=1, abandon_sec=999,
        )
        once = fill_defaults(p, 8, 7, b)
        twice = fill_defaults(once, 8, 7, b)
        self.assertEqual(once.companions, 1)
        self.assertEqual(once.abandon_sec, 999)
        self.assertEqual(once.companions, twice.companions)
        self.assertEqual(once.abandon_sec, twice.abandon_sec)

    def test_batch_gender_counts_match_building_mix(self) -> None:
        b = Building(
            RESIDENTIAL, 0.9, 0.85, 4, (2, 4),
            people_mix={MALE: 0.4, FEMALE: 0.3, CHILD: 0.2, WHEELCHAIR: 0.1},
        )
        pop = b.population(8, 7)
        profiles = make_batch(0, 7, 8, b, population=pop)
        self.assertEqual(len(profiles), pop.total)
        expected = b.category_counts(pop.total)
        actual = {kind: sum(1 for p in profiles if p.gender == kind) for kind in PEOPLE_KINDS}
        self.assertEqual(actual, expected)
        self.assertEqual(sum(actual.values()), pop.total)

    def test_batch_mix_covers_visitors_too(self) -> None:
        # 比例要作用于住客 + 访客全部画像，不只是其中一类
        b = Building(
            RESIDENTIAL, 0.5, 1.0, 4, (2, 4),
            people_mix={MALE: 0.25, FEMALE: 0.25, CHILD: 0.25, WHEELCHAIR: 0.25},
        )
        pop = b.population(8, 7)
        self.assertGreater(pop.visitors, 0)
        self.assertGreater(pop.residents, 0)
        profiles = make_batch(0, 7, 8, b, population=pop)
        for kind in (RESIDENT, VISITOR):
            subset = [p for p in profiles if p.kind == kind]
            self.assertTrue(subset, msg=kind)
            counts = {k: sum(1 for p in subset if p.gender == k) for k in PEOPLE_KINDS}
            self.assertTrue(all(c > 0 for c in counts.values()), msg=f"{kind}: {counts}")

    def test_batch_gender_is_deterministic(self) -> None:
        b = self.only(CHILD, child_min_companions=2)
        a = [p.gender for p in make_batch(0, 7, 8, b)]
        c = [p.gender for p in make_batch(0, 7, 8, b)]
        self.assertEqual(a, c)

    def test_sample_profiles_cover_all_categories(self) -> None:
        self.assertEqual({p.gender for p in sample_profiles()}, set(PEOPLE_KINDS))

    def test_sample_profiles_json_keeps_gender(self) -> None:
        for p in sample_profiles():
            self.assertIn(p.gender, PEOPLE_KINDS)
            self.assertEqual(PassengerProfile.from_json(p.to_json()).gender, p.gender)


class CategoryPropagationTests(unittest.TestCase):
    """人群分类从画像一路传到运行时乘客。"""

    STRATEGY = "algo.zoned"

    def sim_config(self) -> SimConfig:
        # 画像模式必须从 6:00 起跑：样例里最早的作息是 8 点出门，
        # 仿真时间没覆盖到通勤高峰就一个乘客都看不到。
        # dt 取 10 秒足够——事件是按时间戳派发的，粗步长不会漏人。
        return cfg(start_time_min=6 * 60, arrival_rate=0.0)

    @staticmethod
    def live(sim) -> list:
        """仿真里所有活着的乘客：在各层大厅候车的 + 已经在轿厢里的。"""
        out: list = [p for queue in sim.waiting.values() for p in queue]
        for car in sim.elevators:
            out.extend(car.passengers)
        return out

    def run_profile_sim(self):
        """跑满一天，记录全程出现过的分类。"""
        config = self.sim_config()
        sim = Simulation(
            config, create_strategy(self.STRATEGY), ProfileGenerator(config, sample_profiles())
        )
        seen: set[str] = set()
        for _ in range(int(20 * 3600 / 10.0)):
            sim.step(10.0)
            seen |= {p.gender for p in self.live(sim)}
        return sim, seen

    def test_profile_mode_keeps_gender(self) -> None:
        sim, seen = self.run_profile_sim()
        self.assertGreater(sim.metrics.served, 0, msg="整个仿真没有送达任何乘客")
        self.assertTrue(seen <= set(PEOPLE_KINDS), msg=seen)

    def test_profile_mode_children_travel_with_adults(self) -> None:
        # 儿童没有独立的 Passenger.companions 字段：结伴是「同一趟生成
        # 多个乘客」实现的，所以在事件层面验证，且结伴者必须同为儿童。
        child = fill_defaults(
            PassengerProfile(
                pid="C1", name="小朋友", kind=RESIDENT, gender=CHILD, home_floor=5,
            ),
            8, 7, Building(RESIDENTIAL, 0.9, 0.85, 1, (2, 2), child_min_companions=2),
        )
        self.assertGreaterEqual(child.companions, 2)
        gen = ProfileGenerator(self.sim_config(), [child])
        events = gen.pop_until(24 * 3600)
        self.assertTrue(events)
        # 每一趟都是「child.companions 个乘客」一起出发
        by_trip: dict[tuple[float, int, int], list] = {}
        for e in events:
            by_trip.setdefault((e.time, e.origin, e.dest), []).append(e)
        for key, group in by_trip.items():
            self.assertEqual(len(group), child.companions, msg=str(key))
            self.assertEqual({e.gender for e in group}, {CHILD})

    def test_profile_mode_reaches_every_category(self) -> None:
        _, seen = self.run_profile_sim()
        # 9 条样例覆盖四类，跑满一天应当四类都真的进过系统
        self.assertEqual(seen, set(PEOPLE_KINDS))

    def test_random_mode_produces_every_category(self) -> None:
        config = cfg(floors=12, seed=3, passenger_source="random")
        sim = Simulation(config, create_strategy(self.STRATEGY), PassengerGenerator(config))
        for _ in range(int(20 * 3600 / 10.0)):
            sim.step(10.0)
        self.assertEqual({p.gender for p in self.live(sim)}, set(PEOPLE_KINDS))

    def test_random_gender_does_not_disturb_main_stream(self) -> None:
        # 分类走独立随机流：主 RNG 的序列不能因为取分类而错位
        import random

        baseline = random.Random(3)
        expected = [baseline.random() for _ in range(5)]
        real = random.Random(3)
        _random_gender(3, 1)
        self.assertEqual([real.random() for _ in range(5)], expected)

    def test_random_gender_is_deterministic(self) -> None:
        self.assertEqual(_random_gender(3, 1), _random_gender(3, 1))
        self.assertIn(_random_gender(3, 1), PEOPLE_KINDS)
        # 换种子整体应当重新洗牌：单个乘客可能巧合相同，看一批是否覆盖四类
        self.assertEqual({_random_gender(3, pid) for pid in range(40)}, set(PEOPLE_KINDS))


if __name__ == "__main__":
    unittest.main()
