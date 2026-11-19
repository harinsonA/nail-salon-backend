from datetime import timedelta

from django.utils import timezone


class SyncWindow:
    DAYS_BEFORE = 30
    DAYS_AFTER = 60

    def __init__(self, today):
        self.today = today
        self.start = today - timedelta(days=self.DAYS_BEFORE)
        self.end = today + timedelta(days=self.DAYS_AFTER)

    @classmethod
    def current(cls):
        return cls(timezone.localdate())

    @classmethod
    def at(cls, moment):
        return cls(timezone.localdate(moment))

    def as_range(self):
        return (self.start, self.end)
