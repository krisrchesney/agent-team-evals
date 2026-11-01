from .errors import NotFound


class Store:
    def __init__(self):
        self.customers = {}
        self.orders = {}
        self.vouchers = {}

    def get_customer(self, customer_id, param="customer"):
        customer = self.customers.get(customer_id)
        if customer is None:
            raise NotFound(f"no customer {customer_id!r}", param=param)
        return customer

    def get_order(self, order_id):
        order = self.orders.get(order_id)
        if order is None:
            raise NotFound(f"no order {order_id!r}", param="order")
        return order

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def get_voucher(self, voucher_id):
        voucher = self.vouchers.get(voucher_id)
        if voucher is None:
            raise NotFound(f"no voucher {voucher_id!r}", param="voucher")
        return voucher

    def expire_vouchers(self, now):
        for voucher in self.vouchers.values():
            if voucher.status == "active" and voucher.expires_at <= now:
                voucher.status = "expired"
                self.bump(voucher, now)
