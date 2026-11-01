def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def charge_view(charge):
    return {
        "id": charge.id,
        "customer": charge.customer,
        "amount": charge.amount,
        "tax": charge.tax,
        "description": charge.description,
        "refunded": charge.refunded,
        "status": charge.status,
        "created_at": stamp(charge.created_at),
        "updated_at": stamp(charge.updated_at),
        "version": charge.version,
    }


def entry_view(entry):
    return {"id": entry.id, "charge": entry.charge, "kind": entry.kind, "amount": entry.amount,
            "ref": entry.ref, "at": stamp(entry.at)}


def refund_view(refund):
    return {
        "id": refund.id,
        "charge": refund.charge,
        "amount": refund.amount,
        "tax": refund.tax,
        "reason": refund.reason,
        "approved_by": refund.approved_by,
        "created_at": stamp(refund.created_at),
        "updated_at": stamp(refund.updated_at),
        "version": refund.version,
    }
