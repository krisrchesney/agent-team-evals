from .. import validate
from ..errors import Conflict
from ..models import Appointment
from ..views import appointment_view
from .registry import operation


@operation("appointment.book")
def book(svc, params):
    now = svc.clock.now()
    patient = svc.store.get_patient(validate.require_str(params, "patient"))
    start, end = validate.appointment_span(params, now)
    if svc.store.clashes(start, end):
        raise Conflict("the doctor is busy then", param="start")
    appointment = Appointment(id=svc.ids.new("appointment"), patient=patient.id, start=start, end=end,
                              status="booked", created_at=now, updated_at=now)
    svc.store.appointments[appointment.id] = appointment
    view = appointment_view(appointment)
    svc.bus.emit("appointment.booked", {"appointment": view})
    return view


@operation("appointment.cancel")
def cancel(svc, params):
    now = svc.clock.now()
    appointment = svc.store.get_appointment(validate.require_str(params, "appointment"))
    if appointment.status != "booked":
        raise Conflict(f"appointment {appointment.id} is already {appointment.status}", param="appointment")
    appointment.status = "cancelled"
    svc.store.bump(appointment, now)
    view = appointment_view(appointment)
    svc.bus.emit("appointment.cancelled", {"appointment": view})
    return view


@operation("appointment.retrieve")
def retrieve(svc, params):
    return appointment_view(svc.store.get_appointment(validate.require_str(params, "appointment")))


@operation("appointment.list")
def list_appointments(svc, params):
    limit = validate.limit(params)
    if params.get("patient") is not None:
        patient = svc.store.get_patient(validate.require_str(params, "patient"))
        rows = svc.store.appointments_of(patient.id)
    else:
        rows = sorted(svc.store.appointments.values(), key=lambda a: (a.start, a.id))
    return {"data": [appointment_view(a) for a in rows[:limit]], "has_more": len(rows) > limit}
