def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def customer_view(customer):
    return {
        "id": customer.id,
        "name": customer.name,
        "created_at": stamp(customer.created_at),
        "updated_at": stamp(customer.updated_at),
        "version": customer.version,
    }


def line_view(invoice_id, line):
    return {"invoice": invoice_id, "meter": line["meter"], "quantity": line["quantity"],
            "amount": line["amount"]}


def invoice_view(invoice):
    return {
        "id": invoice.id,
        "customer": invoice.customer,
        "lines": [line_view(invoice.id, line) for line in invoice.lines],
        "total": invoice.total,
        "created_at": stamp(invoice.created_at),
    }
