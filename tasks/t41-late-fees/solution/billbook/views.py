def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def balance(invoice):
    """What the customer still owes on this invoice, late fees included."""
    return invoice.amount + invoice.late_fees - invoice.paid


def invoice_view(invoice):
    return {
        "id": invoice.id,
        "customer": invoice.customer,
        "amount": invoice.amount,
        "due": invoice.due.isoformat(),
        "late_fees": invoice.late_fees,
        "paid": invoice.paid,
        "balance": balance(invoice),
        "status": invoice.status,
        "created_at": stamp(invoice.created_at),
        "updated_at": stamp(invoice.updated_at),
        "version": invoice.version,
    }


def payment_view(payment):
    return {"id": payment.id, "invoice": payment.invoice, "amount": payment.amount, "at": stamp(payment.at)}


def fee_view(fee):
    return {"id": fee.id, "invoice": fee.invoice, "amount": fee.amount, "period": fee.period,
            "created_at": stamp(fee.created_at), "updated_at": stamp(fee.updated_at), "version": fee.version}
