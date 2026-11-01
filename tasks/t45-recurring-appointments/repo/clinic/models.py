from dataclasses import dataclass


@dataclass
class Patient:
    id: str
    name: str
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Appointment:
    """A slot with the doctor. There is one doctor, so the whole clinic is one calendar (see Store.clashes)."""
    id: str
    patient: str
    start: object
    end: object
    status: str    # booked | cancelled
    created_at: object
    updated_at: object
    version: int = 1
