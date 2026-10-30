"""The event feed that webhooks are sent from. Which operation emits what: docs/EVENTS.md."""
import copy


class EventBus:
    def __init__(self):
        self.published = []

    def emit(self, type, data, at):
        self.published.append({"type": type, "data": copy.deepcopy(data), "created": at})

    def types(self):
        return [event["type"] for event in self.published]
