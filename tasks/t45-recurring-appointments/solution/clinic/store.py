from .errors import NotFound


class Store:
    def __init__(self):
        self.patients = {}
        self.appointments = {}
        self.series = {}

    def get_patient(self, patient_id, param="patient"):
        patient = self.patients.get(patient_id)
        if patient is None:
            raise NotFound(f"no patient {patient_id!r}", param=param)
        return patient

    def get_appointment(self, appointment_id):
        appointment = self.appointments.get(appointment_id)
        if appointment is None:
            raise NotFound(f"no appointment {appointment_id!r}", param="appointment")
        return appointment

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def appointments_of(self, patient_id):
        return sorted((a for a in self.appointments.values() if a.patient == patient_id), key=lambda a: (a.start, a.id))

    def clashes(self, start, end):
        """Booked appointments that overlap [start, end). Cancelled ones no longer take the slot."""
        return [a for a in self.appointments.values() if a.status == "booked" and a.start < end and start < a.end]

    def get_series(self, series_id):
        series = self.series.get(series_id)
        if series is None:
            raise NotFound(f"no series {series_id!r}", param="series")
        return series
