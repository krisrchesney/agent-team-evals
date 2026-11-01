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
