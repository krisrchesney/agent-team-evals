REACTIONS = []


def reaction(cls):
    """Register a reaction class. The service builds one instance of each."""
    if cls in REACTIONS:
        raise ValueError(f"reaction {cls.__name__} registered twice")
    REACTIONS.append(cls)
    return cls


def build():
    """One instance of every registered reaction, in priority order (lower first)."""
    return [cls() for cls in sorted(REACTIONS, key=lambda cls: cls.priority)]
