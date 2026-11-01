from dataclasses import dataclass


@dataclass
class Staff:
    id: str
    name: str
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Shift:
    """A stretch of work for one person. A person's shifts never overlap (see Store.clashes)."""
    id: str
    staff: str
    start: object
    end: object
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Swap:
    id: str
    shift: str
    from_staff: str
    to_staff: str
    status: str    # pending | accepted | declined | cancelled | expired
    expires_at: object
    created_at: object
    updated_at: object
    version: int = 1
