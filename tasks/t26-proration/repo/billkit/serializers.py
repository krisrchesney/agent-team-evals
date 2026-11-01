"""Plain-dict views of billing objects, for JSON output and exports."""


def line_dict(line):
    return {
        "description": line.description,
        "amount_cents": line.amount_cents,
        "period_start": line.period_start.isoformat(),
        "period_end": line.period_end.isoformat(),
        "kind": line.kind,
    }


def invoice_dict(invoice):
    return {
        "id": invoice.id,
        "customer": invoice.customer,
        "subscription": invoice.subscription,
        "kind": invoice.kind,
        "issued_on": invoice.issued_on.isoformat(),
        "due_on": invoice.due_on.isoformat(),
        "lines": [line_dict(line) for line in invoice.lines],
        "subtotal_cents": invoice.subtotal_cents,
        "tax_cents": invoice.tax_cents,
        "total_cents": invoice.total_cents,
        "paid_on": invoice.paid_on.isoformat() if invoice.paid_on else None,
    }


def subscription_dict(sub):
    return {
        "id": sub.id,
        "customer": sub.customer,
        "plan": sub.plan,
        "quantity": sub.quantity,
        "start": sub.start.isoformat(),
        "anchor_day": sub.anchor_day,
        "status": sub.status,
        "canceled_on": sub.canceled_on.isoformat() if sub.canceled_on else None,
    }


def plan_dict(plan):
    return {"id": plan.id, "name": plan.name, "interval": plan.interval, "price_cents": plan.price_cents,
            "included_units": plan.included_units}
