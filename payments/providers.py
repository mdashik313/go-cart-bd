import secrets

# base payment class

class PaymentProvider:
    name = "BASE"

    def initiate_payment(self, payment):
        raise NotImplementedError

    def refund_payment(self, payment, amount):
        raise NotImplementedError


class MockPaymentProvider(PaymentProvider):
    """Simulates a gateway for this project without real account"""

    name = "MOCK"

    def initiate_payment(self, payment):
        provider_transaction_id = f"MOCK-{secrets.randbelow(900000) + 100000}"
        return {"provider_transaction_id": provider_transaction_id, "status": "PROCESSING"}

    def refund_payment(self, payment, amount):
        provider_refund_id = f"MOCK-REFUND-{secrets.randbelow(90000) + 10000}"
        return {"provider_refund_id": provider_refund_id, "status": "COMPLETED"}


PROVIDERS = {"MOCK": MockPaymentProvider()}


def get_payment_provider(name="MOCK"):
    return PROVIDERS.get(name, PROVIDERS["MOCK"])
