def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def contact_view(contact):
    return {
        "id": contact.id,
        "name": contact.name,
        "emails": list(contact.emails),
        "phones": list(contact.phones),
        "company": contact.company,
        "created_at": stamp(contact.created_at),
        "updated_at": stamp(contact.updated_at),
        "version": contact.version,
    }


def activity_view(activity):
    return {"id": activity.id, "contact": activity.contact, "kind": activity.kind, "note": activity.note,
            "at": stamp(activity.at)}
