def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def staff_view(person):
    return {"id": person.id, "name": person.name, "created_at": stamp(person.created_at),
            "updated_at": stamp(person.updated_at), "version": person.version}


def shift_view(shift):
    return {"id": shift.id, "staff": shift.staff, "start": stamp(shift.start), "end": stamp(shift.end),
            "created_at": stamp(shift.created_at), "updated_at": stamp(shift.updated_at),
            "version": shift.version}
