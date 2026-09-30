from __future__ import annotations

from collections import deque

from core.models import Elevator, ElevatorPhase, Passenger, PassengerState, SimConfig
from core.passenger import PassengerGenerator
from core.stats import MetricsCollector


class Simulation:
    def __init__(
        self,
        config: SimConfig,
        strategy,
        generator: PassengerGenerator | None = None,
    ):
        self.config = config.normalized()
        self.strategy = strategy
        self.generator = generator or PassengerGenerator(self.config)
        self.elevators = [
            Elevator(eid=i, floor=1.0) for i in range(self.config.elevators)
        ]
        self.now = 0.0
        self.waiting: dict[int, list[Passenger]] = {
            f: [] for f in range(1, self.config.floors + 1)
        }
        self.assigned: set[tuple[int, int]] = set()
        self.arrival_log: deque[tuple[float, int]] = deque()
        self.metrics = MetricsCollector()
        self._pid = 0

    @property
    def floors(self) -> int:
        return self.config.floors

    def step(self, dt: float) -> None:
        self.now += dt
        top = self.config.floors
        for event in self.generator.pop_until(self.now):
            origin = min(top, max(1, int(event.origin)))
            dest = min(top, max(1, int(event.dest)))
            if origin == dest:
                continue
            p = Passenger(
                pid=event.pid,
                origin=origin,
                dest=dest,
                arrive_time=event.time,
                deadline=event.deadline,
                gender=event.gender,
            )
            self.waiting[origin].append(p)
            self.arrival_log.append((event.time, origin))
            self.metrics.on_arrival()
        self._prune_arrival_log()
        self._check_abandoned()
        self._dispatch()
        for e in self.elevators:
            self._update_elevator(e, dt)
        self.metrics.maybe_sample(self.now)

    def _prune_arrival_log(self) -> None:
        cutoff = self.now - self.config.history_window
        log = self.arrival_log
        while log and log[0][0] < cutoff:
            log.popleft()

    def _check_abandoned(self) -> None:
        if not self.config.allow_abandon:
            return
        for floor, passengers in self.waiting.items():
            if not passengers:
                continue
            keep: list[Passenger] = []
            for p in passengers:
                if p.deadline is not None and self.now > p.deadline:
                    p.state = PassengerState.ABANDONED
                    self.metrics.on_abandon()
                else:
                    keep.append(p)
            if len(keep) != len(passengers):
                self.waiting[floor] = keep
                self._release_stale_assignments(floor)

    def _release_stale_assignments(self, floor: int) -> None:
        for dir_ in (1, -1):
            if (floor, dir_) in self.assigned and not self.waiting_passengers(floor, dir_):
                self.assigned.discard((floor, dir_))

    def call_distribution(
        self, window: float | None = None, floors: int | None = None
    ) -> dict[int, float]:
        n = floors or self.floors
        counts = [0.0] * (n + 1)
        cutoff = self.now - window if window is not None else float("-inf")
        total = 0.0
        for t, f in self.arrival_log:
            if t < cutoff or f > n:
                continue
            counts[f] += 1.0
            total += 1.0
        if total <= 0:
            return {f: 1.0 / n for f in range(1, n + 1)}
        return {f: counts[f] / total for f in range(1, n + 1)}

    def waiting_passengers(self, floor: int, dir_: int | None = None) -> list[Passenger]:
        out = []
        for p in self.waiting.get(floor, []):
            if dir_ is None or p.dir == dir_:
                out.append(p)
        return out

    def _dispatch(self) -> None:
        for floor in range(1, self.floors + 1):
            dirs = {p.dir for p in self.waiting.get(floor, [])}
            for dir_ in dirs:
                if (floor, dir_) in self.assigned:
                    continue
                e = self._best_elevator(floor)
                if e is None:
                    continue
                e.pickups.add((floor, dir_))
                self.assigned.add((floor, dir_))
                if e.phase == ElevatorPhase.IDLE:
                    self._start_motion(e)

    def _best_elevator(self, floor: int) -> Elevator | None:
        best: Elevator | None = None
        best_score = float("inf")
        for e in self.elevators:
            idle_factor = 1.0 if e.phase == ElevatorPhase.IDLE else 1.6
            score = abs(e.floor - floor) * idle_factor + 0.75 * len(e.pickups)
            if score < best_score:
                best_score = score
                best = e
        return best

    def _service_targets(self, e: Elevator) -> list[int]:
        targets = set(e.calls)
        targets.update(f for f, _ in e.pickups)
        return sorted(targets)

    def _start_motion(self, e: Elevator) -> None:
        targets = self._service_targets(e)
        floor_i = int(round(e.floor))
        if abs(e.floor - floor_i) < 1e-9 and floor_i in targets:
            self._arrive(e, floor_i)
            return
        if not targets:
            if e.park_target is not None and int(round(e.floor)) != e.park_target:
                targets = [e.park_target]
            else:
                e.phase = ElevatorPhase.IDLE
                e.direction = 0
                e.idle_time = 0.0
                return
        ahead = [t for t in targets if (t - e.floor) * e.direction > 1e-9]
        if not ahead:
            if e.direction == 0:
                nearest = min(targets, key=lambda t: abs(t - e.floor))
                e.direction = 1 if nearest > e.floor else -1
            else:
                others = [t for t in targets if t != e.floor]
                if not others:
                    e.phase = ElevatorPhase.IDLE
                    e.direction = 0
                    return
                nearest = min(others, key=lambda t: abs(t - e.floor))
                e.direction = 1 if nearest > e.floor else -1
        e.phase = ElevatorPhase.MOVING

    def _next_stop(self, e: Elevator) -> int | None:
        targets = self._service_targets(e)
        if not targets:
            if e.park_target is not None:
                targets = [e.park_target]
            else:
                return None
        ahead = [t for t in targets if (t - e.floor) * e.direction > 1e-9]
        if ahead:
            if e.direction > 0:
                return min(ahead)
            return max(ahead)
        behind = [t for t in targets if t != e.floor]
        if behind:
            nearest = min(behind, key=lambda t: abs(t - e.floor))
            if abs(nearest - e.floor) < 1e-9:
                return None
            e.direction = 1 if nearest > e.floor else -1
            return nearest
        return None

    def _update_elevator(self, e: Elevator, dt: float) -> None:
        phase = e.phase
        if phase == ElevatorPhase.IDLE:
            self._update_idle(e, dt)
        elif phase == ElevatorPhase.MOVING:
            self._update_moving(e, dt)
        elif phase == ElevatorPhase.OPENING:
            self._update_opening(e, dt)
        elif phase == ElevatorPhase.OPEN:
            self._update_open(e, dt)
        elif phase == ElevatorPhase.CLOSING:
            self._update_closing(e, dt)

    def _update_idle(self, e: Elevator, dt: float) -> None:
        if e.pickups or e.calls:
            self._start_motion(e)
            return
        e.idle_time += dt
        if e.idle_time < self.config.idle_park_delay:
            return
        target = int(self.strategy.decide(e, self))
        target = min(self.floors, max(1, target))
        e.park_target = target
        e.idle_time = 0.0
        if target != int(round(e.floor)):
            e.direction = 1 if target > e.floor else -1
            e.phase = ElevatorPhase.MOVING

    def _update_moving(self, e: Elevator, dt: float) -> None:
        stop = self._next_stop(e)
        if stop is None:
            if e.calls or e.pickups:
                self._start_motion(e)
                if e.phase != ElevatorPhase.MOVING:
                    return
                stop = self._next_stop(e)
                if stop is None:
                    e.phase = ElevatorPhase.IDLE
                    e.direction = 0
                    return
            else:
                e.phase = ElevatorPhase.IDLE
                e.direction = 0
                return
        step = self.config.speed * dt
        dist = stop - e.floor
        if dist * e.direction <= step:
            self.metrics.on_travel(abs(dist))
            e.floor = float(stop)
            self._arrive(e, stop)
        else:
            e.floor += step * e.direction
            self.metrics.on_travel(step)

    def _arrive(self, e: Elevator, stop: int) -> None:
        will_alight = any(p.dest == stop for p in e.passengers)
        boardable = self._boardable(e, stop)
        if will_alight or boardable:
            e.phase = ElevatorPhase.OPENING
            e.open_elapsed = 0.0
            e.dwell_elapsed = 0.0
            e.board_cooldown = 0.0
        else:
            stale = {pr for pr in e.pickups if pr[0] == stop}
            for pr in stale:
                e.pickups.discard(pr)
                self.assigned.discard(pr)
            if e.calls or e.pickups:
                self._start_motion(e)
            else:
                e.phase = ElevatorPhase.IDLE
                e.direction = 0

    def _boardable(self, e: Elevator, floor: int) -> list[Passenger]:
        out: list[Passenger] = []
        for pr in e.pickups:
            if pr[0] != floor:
                continue
            out.extend(self.waiting_passengers(floor, pr[1]))
        return out

    def _update_opening(self, e: Elevator, dt: float) -> None:
        if self.config.door_time <= 0:
            e.door = 1.0
            e.phase = ElevatorPhase.OPEN
            e.open_elapsed = 0.0
            return
        e.door += dt / self.config.door_time
        if e.door >= 1.0:
            e.door = 1.0
            e.phase = ElevatorPhase.OPEN
            e.open_elapsed = 0.0

    def _update_open(self, e: Elevator, dt: float) -> None:
        e.open_elapsed += dt
        floor = int(round(e.floor))
        if e.board_cooldown > 0:
            e.board_cooldown -= dt
            return
        alight = next((p for p in e.passengers if p.dest == floor), None)
        if alight is not None:
            e.passengers.remove(alight)
            alight.state = PassengerState.DONE
            alight.done_time = self.now
            e.calls.discard(alight.dest)
            self.metrics.on_served()
            e.board_cooldown = self.config.alighting_time
            return
        board = self._next_board_passenger(e, floor)
        if board is not None:
            p, pickup_key = board
            self.waiting[floor].remove(p)
            p.state = PassengerState.RIDING
            p.board_time = self.now
            p.elevator_id = e.eid
            e.passengers.append(p)
            e.calls.add(p.dest)
            self.metrics.on_boarding(p.wait_time)
            if not self.waiting_passengers(floor, pickup_key[1]):
                e.pickups.discard(pickup_key)
                e.served_pickups.add(pickup_key)
                self.assigned.discard(pickup_key)
            e.board_cooldown = self.config.boarding_time
            return
        done_alighting = not any(p.dest == floor for p in e.passengers)
        if done_alighting and e.open_elapsed >= self.config.min_door_open:
            e.phase = ElevatorPhase.CLOSING

    def _next_board_passenger(
        self, e: Elevator, floor: int
    ) -> tuple[Passenger, tuple[int, int]] | None:
        for pr in sorted(e.pickups):
            if pr[0] != floor:
                continue
            waiting = self.waiting_passengers(floor, pr[1])
            if waiting:
                return waiting[0], pr
        return None

    def _update_closing(self, e: Elevator, dt: float) -> None:
        if self.config.door_time <= 0:
            e.door = 0.0
        else:
            e.door -= dt / self.config.door_time
        if e.door > 0:
            return
        e.door = 0.0
        if e.calls or e.pickups:
            self._start_motion(e)
        elif e.park_target is not None and int(round(e.floor)) != e.park_target:
            e.direction = 1 if e.park_target > e.floor else -1
            e.phase = ElevatorPhase.MOVING
        else:
            e.phase = ElevatorPhase.IDLE
            e.direction = 0
            e.idle_time = 0.0

    def waiting_count(self) -> int:
        return sum(len(v) for v in self.waiting.values())
