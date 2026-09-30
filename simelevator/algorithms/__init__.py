from __future__ import annotations

from algorithms.base import REGISTRY, ParkingStrategy, register

from algorithms import strategies as _strategies  # noqa: F401

__all__ = ["REGISTRY", "ParkingStrategy", "register", "create_strategy"]


def create_strategy(key: str) -> ParkingStrategy:
    if key not in REGISTRY:
        raise KeyError(f"unknown strategy: {key}")
    return REGISTRY[key]()
