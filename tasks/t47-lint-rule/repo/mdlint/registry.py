RULES = {}


def register(name):
    def add(cls):
        if name in RULES:
            raise ValueError(f"rule type {name!r} registered twice")
        cls.type = name
        RULES[name] = cls
        return cls
    return add
