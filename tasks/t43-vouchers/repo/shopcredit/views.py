def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def customer_view(customer):
    return {"id": customer.id, "name": customer.name, "created_at": stamp(customer.created_at),
            "updated_at": stamp(customer.updated_at), "version": customer.version}


def order_view(order):
    return {"id": order.id, "customer": order.customer, "total": order.total, "status": order.status,
            "created_at": stamp(order.created_at), "updated_at": stamp(order.updated_at),
            "version": order.version}
