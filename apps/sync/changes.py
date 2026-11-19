from apps.sync.feeds import AppointmentFeed, CategoryFeed, ClientFeed, ServiceFeed
from apps.sync.mark import SyncMark
from apps.sync.window import SyncWindow


class SyncChanges:
    def __init__(self, user, since):
        self.user = user
        self.mark = SyncMark(since)
        self.window = SyncWindow.current()
        self.feeds = {
            "appointments": AppointmentFeed(user, self.mark, self.window),
            "clients": ClientFeed(self.mark),
            "categories": CategoryFeed(self.mark),
            "services": ServiceFeed(self.mark),
        }

    def build(self):
        return {
            "mark": self.mark.next(),
            "full": self.mark.is_full,
            "window": {"start": self.window.start, "end": self.window.end},
            **{name: list(feed.items()) for name, feed in self.feeds.items()},
            "removed": {name: feed.removed() for name, feed in self.feeds.items()},
        }
