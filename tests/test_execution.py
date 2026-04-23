from agent.execution import PaperExecutor, decision_to_order_request
from agent.models import TradeDecision


def test_decision_to_order_request_none_for_hold():
    decision = TradeDecision(
        market_id="m1",
        signal="HOLD",
        target_price=0.5,
        edge=0.0,
        size_usd=0.0,
        confidence=0.6,
        expected_value_bps=0.0,
        source_health=1.0,
        regime="LOW_VOL",
        rationale="hold",
    )
    assert decision_to_order_request(decision) is None


def test_paper_executor_accepts_valid_order():
    decision = TradeDecision(
        market_id="m1",
        signal="BUY",
        target_price=0.62,
        edge=0.05,
        size_usd=100.0,
        confidence=0.8,
        expected_value_bps=500,
        source_health=1.0,
        regime="LOW_VOL",
        rationale="buy",
    )
    request = decision_to_order_request(decision)
    assert request is not None

    result = PaperExecutor(max_notional_usd=200).submit_order(request)
    assert result.accepted is True
    assert result.order_id is not None
