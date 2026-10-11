class S0StubError(RuntimeError):
    pass
class CheckoutSessionRequest:
    def __init__(self, *a, **k):
        raise S0StubError("S0 stub: payments unavailable")
class StripeCheckout:
    def __init__(self, *a, **k):
        raise S0StubError("S0 stub: payments unavailable")
