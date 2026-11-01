def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def staff_view(person):
    return {"id": person.id, "name": person.name, "created_at": stamp(person.created_at),
            "updated_at": stamp(person.updated_at), "version": person.version}


def shift_view(shift):
    return {"id": shift.id, "staff": shift.staff, "start": stamp(shift.start), "end": stamp(shift.end),
            "created_at": stamp(shift.created_at), "updated_at": stamp(shift.updated_at),
            "version": shift.version}


def swap_view(swap):
    return {"id": swap.id, "shift": swap.shift, "from_staff": swap.from_staff, "to_staff": swap.to_staff,
            "status": swap.status, "expires_at": stamp(swap.expires_at), "created_at": stamp(swap.created_at),
            "updated_at": stamp(swap.updated_at), "version": swap.version}
