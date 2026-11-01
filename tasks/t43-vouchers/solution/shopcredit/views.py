def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def customer_view(customer):
    return {"id": customer.id, "name": customer.name, "created_at": stamp(customer.created_at),
            "updated_at": stamp(customer.updated_at), "version": customer.version}


def order_view(order):
    return {"id": order.id, "customer": order.customer, "total": order.total, "credited": order.credited,
            "status": order.status, "created_at": stamp(order.created_at), "updated_at": stamp(order.updated_at),
            "version": order.version}


def voucher_view(voucher):
    return {"id": voucher.id, "amount": voucher.amount, "balance": voucher.balance, "status": voucher.status,
            "expires_at": stamp(voucher.expires_at), "created_at": stamp(voucher.created_at),
            "updated_at": stamp(voucher.updated_at), "version": voucher.version}
