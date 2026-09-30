from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Sample:
    time: float
    awt: float
    travel: float
    served: int


@dataclass
class MetricsCollector:
    arrived: int = 0
    boarded: int = 0
    served: int = 0
    abandoned: int = 0
    total_wait: float = 0.0
    travel_floors: float = 0.0
    samples: list[Sample] = field(default_factory=list)
    _last_sample_time: float = -1e9

    def on_arrival(self) -> None:
        self.arrived += 1

    def on_boarding(self, wait: float) -> None:
        self.boarded += 1
        self.total_wait += wait

    def on_served(self) -> None:
        self.served += 1

    def on_abandon(self) -> None:
        self.abandoned += 1

    def on_travel(self, floors: float) -> None:
        self.travel_floors += floors

    @property
    def awt(self) -> float:
        return self.total_wait / self.boarded if self.boarded else 0.0

    @property
    def waiting(self) -> int:
        return self.arrived - self.boarded - self.abandoned

    @property
    def abandon_rate(self) -> float:
        total = self.boarded + self.abandoned
        return self.abandoned / total if total else 0.0

    def maybe_sample(self, now: float, interval: float = 1.0) -> None:
        if now - self._last_sample_time < interval:
            return
        self._last_sample_time = now
        self.samples.append(
            Sample(time=now, awt=self.awt, travel=self.travel_floors, served=self.served)
        )
        if len(self.samples) > 3600:
            del self.samples[:1800]

    def snapshot(self) -> dict[str, float]:
        return {
            "awt": self.awt,
            "travel": self.travel_floors,
            "arrived": float(self.arrived),
            "boarded": float(self.boarded),
            "served": float(self.served),
            "abandoned": float(self.abandoned),
            "abandon_rate": self.abandon_rate,
            "waiting": float(self.waiting),
        }
