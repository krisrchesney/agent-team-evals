import calendar
from datetime import timedelta

from .. import validate
from ..errors import Conflict, InvalidRequest
from ..models import Appointment, Series
from ..views import series_view
from .registry import operation

REPEATS = ("weekly", "monthly")
MIN_COUNT, MAX_COUNT = 2, 12


def _occurrences(first, repeat, count):
    """Start times of every occurrence. Monthly ones keep the first one's day, or the month's last day if shorter."""
    if repeat == "weekly":
        return [first + timedelta(days=7 * i) for i in range(count)]
    out = []
    for i in range(count):
        month0 = first.month - 1 + i
        year, month = first.year + month0 // 12, month0 % 12 + 1
        day = min(first.day, calendar.monthrange(year, month)[1])
        out.append(first.replace(year=year, month=month, day=day))
    return out


def _count(params):
    value = params.get("count")
    if isinstance(value, bool) or not isinstance(value, int) or not MIN_COUNT <= value <= MAX_COUNT:
        raise InvalidRequest(f"count must be a whole number from {MIN_COUNT} to {MAX_COUNT}", param="count")
    return value


@operation("series.create")
def create(svc, params):
    now = svc.clock.now()
    patient = svc.store.get_patient(validate.require_str(params, "patient"))
    first, end = validate.appointment_span(params, now)
    length = end - first
    repeat = validate.require_str(params, "repeat")
    if repeat not in REPEATS:
        raise InvalidRequest("repeat must be weekly or monthly", param="repeat")
    count = _count(params)
    if any(s.patient == patient.id and s.status == "active" for s in svc.store.series.values()):
        raise Conflict(f"{patient.name} already has a series", param="patient")
    starts = _occurrences(first, repeat, count)
    if svc.store.clashes(starts[0], starts[0] + length):
        raise Conflict("the doctor is busy at the first date", param="start")
    booked = [s for s in starts if not svc.store.clashes(s, s + length)]
    skipped = [s for s in starts if s not in booked]
    ids = []
    for s in booked:
        appointment = Appointment(id=svc.ids.new("appointment"), patient=patient.id, start=s, end=s + length,
                                  status="booked", created_at=now, updated_at=now)
        svc.store.appointments[appointment.id] = appointment
        ids.append(appointment.id)
    series = Series(id=svc.ids.new("series"), patient=patient.id, repeat=repeat, status="active",
                    appointments=ids, skipped=skipped, created_at=now, updated_at=now)
    svc.store.series[series.id] = series
    view = series_view(series)
    svc.bus.emit("series.created", {"series": view})
    return view


@operation("series.cancel")
def cancel(svc, params):
    now = svc.clock.now()
    series = svc.store.get_series(validate.require_str(params, "series"))
    if series.status != "active":
        raise Conflict(f"series {series.id} is already {series.status}", param="series")
    for appointment_id in series.appointments:
        appointment = svc.store.get_appointment(appointment_id)
        if appointment.status == "booked" and appointment.start > now:
            appointment.status = "cancelled"
            svc.store.bump(appointment, now)
    series.status = "cancelled"
    svc.store.bump(series, now)
    view = series_view(series)
    svc.bus.emit("series.cancelled", {"series": view})
    return view


@operation("series.retrieve")
def retrieve(svc, params):
    return series_view(svc.store.get_series(validate.require_str(params, "series")))
