from .. import validate
from ..models import Patient
from ..views import patient_view
from .registry import operation


@operation("patient.create")
def create(svc, params):
    now = svc.clock.now()
    name = validate.require_str(params, "name")
    patient = Patient(id=svc.ids.new("patient"), name=name, created_at=now, updated_at=now)
    svc.store.patients[patient.id] = patient
    view = patient_view(patient)
    svc.bus.emit("patient.created", {"patient": view})
    return view


@operation("patient.retrieve")
def retrieve(svc, params):
    return patient_view(svc.store.get_patient(validate.require_str(params, "patient")))
