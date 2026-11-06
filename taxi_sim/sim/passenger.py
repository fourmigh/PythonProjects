"""乘客 Agent 状态机: waiting → onboard → delivered / expired(耐心超时)。"""
import time


class Passenger:
    __slots__ = ("pid", "origin", "dest", "state", "born", "assigned_taxi")

    WAITING = "waiting"
    ONBOARD = "onboard"
    DELIVERED = "delivered"
    EXPIRED = "expired"

    def __init__(self, pid, origin, dest, patience):
        self.pid = pid
        self.origin = origin      # (lat,lng)
        self.dest = dest
        self.state = self.WAITING
        self.born = time.monotonic()
        self.assigned_taxi = None

    @property
    def position(self):
        return self.dest if self.state == self.ONBOARD else self.origin

    def wait_seconds(self, now):
        return now - self.born

    def is_expired(self, now, patience):
        return (self.state == self.WAITING
                and self.wait_seconds(now) > patience)
