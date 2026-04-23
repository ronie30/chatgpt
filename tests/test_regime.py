from agent.data_sources import DataBundle, SourceDiagnostics
from agent.models import MarketFeatures, OrderBookSnapshot
from agent.regime import detect_regime


def _features() -> MarketFeatures:
    return MarketFeatures(
        market_id="m1",
        implied_probability=0.5,
        fair_probability=0.52,
        sentiment_score=0.6,
        news_score=0.6,
        onchain_flow_score=0.6,
        orderflow_imbalance=0.1,
        liquidity_score=0.8,
        confidence=0.8,
        disagreement_penalty=0.0,
        source_health=1.0,
    )


def _bundle(best_bid: float, best_ask: float, s: float, n: float, o: float) -> DataBundle:
    return DataBundle(
        implied_probability=0.5,
        orderbook=OrderBookSnapshot(
            best_bid=best_bid,
            best_ask=best_ask,
            last_trade_price=(best_bid + best_ask) / 2,
            bid_depth=1000,
            ask_depth=1000,
        ),
        sentiment_score=s,
        news_score=n,
        onchain_flow_score=o,
        diagnostics=SourceDiagnostics(True, True, True, True, True, True),
    )


def test_detect_regime_high_vol():
    bundle = _bundle(0.20, 0.80, 0.9, -0.8, 0.7)
    features = _features()
    features.sentiment_score = 0.9
    features.news_score = -0.8
    features.onchain_flow_score = 0.7

    regime = detect_regime(bundle, features)
    assert regime.label == "HIGH_VOL"
    assert regime.risk_multiplier < 1.0


def test_detect_regime_low_vol():
    bundle = _bundle(0.49, 0.51, 0.2, 0.25, 0.15)
    features = _features()
    features.sentiment_score = 0.2
    features.news_score = 0.25
    features.onchain_flow_score = 0.15

    regime = detect_regime(bundle, features)
    assert regime.label == "LOW_VOL"
