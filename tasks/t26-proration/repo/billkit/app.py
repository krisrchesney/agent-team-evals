"""The `Billing` object: every repository and the operations on them in one place."""
from . import cancellation, plan_change, quotas, revenue, seats, subscriptions
from .api_keys import ApiKeyRepo
from .addresses import AddressRepo
from .catalog import Catalog
from .contacts import ContactRepo
from .coupons import CouponRepo
from .credits import CreditLedger
from .customers import CustomerRepo
from .events import EventLog
from .invoices import InvoiceBook
from .labels import LabelRepo
from .notes import NoteRepo
from .payment_methods import PaymentMethodRepo
from .price_books import PriceBookRepo
from .products import ProductRepo
from .subscriptions import SubscriptionRepo
from .tax_rates import TaxRateRepo
from .invoice_templates import InvoiceTemplateRepo
from .bank_accounts import BankAccountRepo
from .vat_ids import VatIdRepo
from .discount_rules import DiscountRuleRepo
from .dunning_policies import DunningPolicyRepo
from .currencies import CurrencyRepo
from .sales_reps import SalesRepRepo
from .credit_reasons import CreditReasonRepo
from .payout_schedules import PayoutScheduleRepo
from .ledger_accounts import LedgerAccountRepo
from .tickets import TicketRepo
from .regions import RegionRepo
from .usage import UsageLog
from .webhooks import WebhookEndpointRepo


class Billing:
    def __init__(self):
        self.events = EventLog()
        self.catalog = Catalog()
        self.customers = CustomerRepo()
        self.addresses = AddressRepo()
        self.contacts = ContactRepo()
        self.coupons = CouponRepo()
        self.tax_rates = TaxRateRepo()
        self.products = ProductRepo()
        self.payment_methods = PaymentMethodRepo()
        self.webhooks = WebhookEndpointRepo()
        self.notes = NoteRepo()
        self.labels = LabelRepo()
        self.api_keys = ApiKeyRepo()
        self.price_books = PriceBookRepo()
        self.invoice_templates = InvoiceTemplateRepo()
        self.bank_accounts = BankAccountRepo()
        self.vat_ids = VatIdRepo()
        self.discount_rules = DiscountRuleRepo()
        self.dunning_policies = DunningPolicyRepo()
        self.currencies = CurrencyRepo()
        self.sales_reps = SalesRepRepo()
        self.credit_reasons = CreditReasonRepo()
        self.payout_schedules = PayoutScheduleRepo()
        self.ledger_accounts = LedgerAccountRepo()
        self.tickets = TicketRepo()
        self.regions = RegionRepo()
        self.subscriptions = SubscriptionRepo()
        self.invoices = InvoiceBook()
        self.credits = CreditLedger()
        self.usage = UsageLog()

    def subscribe(self, customer_id, plan_id, start, quantity=1, anchor_day=1):
        return subscriptions.create(self, customer_id, plan_id, start, quantity, anchor_day)

    def change_plan(self, sub_id, new_plan_id, on):
        return plan_change.change_plan(self, sub_id, new_plan_id, on)

    def cancel(self, sub_id, on):
        return cancellation.cancel(self, sub_id, on)

    def add_seats(self, sub_id, count, on):
        return seats.add_seats(self, sub_id, count, on)

    def remove_seats(self, sub_id, count):
        return seats.remove_seats(self, sub_id, count)

    def allowance(self, sub_id, on):
        return quotas.allowance(self, sub_id, on)

    def recognized(self, invoice_id, index, as_of):
        return revenue.recognized_cents(self, invoice_id, index, as_of)
