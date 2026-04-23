from agent.data_sources import DataBundle, SourceDiagnostics
from agent.models import OrderBookSnapshot
from agent.quality import DataQualityGuard


def _bundle(implied: float, bid: float, ask: float, bid_depth: float = 1000, ask_depth: float = 1000) -> DataBundle:
    return DataBundle(
        implied_probability=implied,
        orderbook=OrderBookSnapshot(
            best_bid=bid,
            best_ask=ask,
            last_trade_price=(bid + ask) / 2,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
        ),
        sentiment_score=0.1,
        news_score=0.1,
        onchain_flow_score=0.1,
        diagnostics=SourceDiagnostics(True, True, True, True, True, True),
    )


def test_quality_guard_detects_outlier_after_history():
    guard = DataQualityGuard(window=20)

    for _ in range(15):
        q = guard.assess("m1", _bundle(0.5, 0.49, 0.51, 1000, 1000))
        assert q.quality_score >= 0.75

    outlier = guard.assess("m1", _bundle(0.95, 0.1, 0.9, 50, 60))
    assert outlier.quality_score < 0.75
    assert len(outlier.anomalies) >= 1
