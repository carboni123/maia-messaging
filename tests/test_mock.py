"""Tests for the MockProvider."""

from messaging import DeliveryResult, MockProvider, WhatsAppText


class TestMockProvider:
    def test_records_sent_messages(self):
        provider = MockProvider()
        msg = WhatsAppText(to="+5511999999999", body="Hello")
        result = provider.send(msg)

        assert result.succeeded
        assert len(provider.sent) == 1
        assert provider.sent[0].message is msg
        assert provider.sent[0].result is result

    def test_fixed_result(self):
        failure = DeliveryResult.fail("quota exceeded")
        provider = MockProvider(fixed_result=failure)
        result = provider.send(WhatsAppText(to="+5511999999999", body="Hi"))

        assert not result.succeeded
        assert result.error_message == "quota exceeded"

    def test_failure_rate(self):
        # With 100% failure rate, every send should fail
        provider = MockProvider(failure_rate=1.0)
        results = [provider.send(WhatsAppText(to="+5511999999999", body="Hi")) for _ in range(10)]

        assert all(not r.succeeded for r in results)
        assert len(provider.sent) == 10

    def test_zero_failure_rate(self):
        provider = MockProvider(failure_rate=0.0)
        results = [provider.send(WhatsAppText(to="+5511999999999", body="Hi")) for _ in range(10)]

        assert all(r.succeeded for r in results)

    def test_fetch_status_for_sent_message(self):
        provider = MockProvider()
        result = provider.send(WhatsAppText(to="+5511999999999", body="Hi"))
        ext_id = result.external_id

        fetched = provider.fetch_status(ext_id)
        assert fetched is not None
        assert fetched.external_id == ext_id

    def test_fetch_status_unknown_id(self):
        provider = MockProvider()
        assert provider.fetch_status("unknown") is None

    def test_reset_clears_sent(self):
        provider = MockProvider()
        provider.send(WhatsAppText(to="+5511999999999", body="Hi"))
        assert len(provider.sent) == 1

        provider.reset()
        assert len(provider.sent) == 0
