class S0StubError(RuntimeError):
    pass
class UserMessage:
    def __init__(self, text=None, **kw):
        self.text = text
class LlmChat:
    def __init__(self, *a, **k):
        pass
    def with_model(self, *a, **k):
        return self
    async def send_message(self, *a, **k):
        raise S0StubError("S0 stub: external inference unavailable (emergentintegrations not installable)")
