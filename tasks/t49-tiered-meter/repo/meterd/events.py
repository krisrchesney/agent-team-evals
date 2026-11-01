class Bus:
    def __init__(self):
        self.log = []
        self._subscribers = []

    def subscribe(self, fn):
        self._subscribers.append(fn)

    def emit(self, type_, data):
        event = {"type": type_, "data": data}
        self.log.append(event)
        for fn in self._subscribers:
            fn(event)
