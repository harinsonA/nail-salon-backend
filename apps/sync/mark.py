from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime


class SyncMark:
    MAX_AGE = timedelta(days=30)
    OVERLAP = timedelta(seconds=60)

    def __init__(self, value, now=None):
        self.now = now or timezone.now()
        self.moment = self.parse(value)

    def parse(self, value):
        if not value:
            return None
        try:
            moment = parse_datetime(value)
        except ValueError:
            return None
        if moment is None or timezone.is_naive(moment):
            return None
        if moment > self.now or self.now - moment > self.MAX_AGE:
            return None
        return moment

    @property
    def is_full(self):
        return self.moment is None

    @property
    def changed_since(self):
        return self.moment - self.OVERLAP

    def next(self):
        return self.now.isoformat()
