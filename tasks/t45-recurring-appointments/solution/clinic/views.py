def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def patient_view(patient):
    return {"id": patient.id, "name": patient.name, "created_at": stamp(patient.created_at),
            "updated_at": stamp(patient.updated_at), "version": patient.version}


def appointment_view(appointment):
    return {"id": appointment.id, "patient": appointment.patient, "start": stamp(appointment.start),
            "end": stamp(appointment.end), "status": appointment.status,
            "created_at": stamp(appointment.created_at), "updated_at": stamp(appointment.updated_at),
            "version": appointment.version}


def series_view(series):
    return {"id": series.id, "patient": series.patient, "repeat": series.repeat, "status": series.status,
            "appointments": list(series.appointments), "skipped": [stamp(s) for s in series.skipped],
            "created_at": stamp(series.created_at), "updated_at": stamp(series.updated_at),
            "version": series.version}
