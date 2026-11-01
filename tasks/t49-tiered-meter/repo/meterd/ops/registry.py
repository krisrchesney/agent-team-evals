OPERATIONS = {}


def operation(name):
    def register(fn):
        if name in OPERATIONS:
            raise ValueError(f"operation {name!r} registered twice")
        OPERATIONS[name] = fn
        return fn
    return register
