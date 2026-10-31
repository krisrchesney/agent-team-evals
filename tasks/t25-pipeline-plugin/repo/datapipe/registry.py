PLUGINS = {}


def register(name):
    def add(cls):
        if name in PLUGINS:
            raise ValueError(f"stage type {name!r} registered twice")
        cls.type = name
        PLUGINS[name] = cls
        return cls
    return add
