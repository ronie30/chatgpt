from agent.config import APIConfig, StrategyConfig
from agent.data_sources import DataBundle, PolymarketDataClient, SourceDiagnostics
from agent.models import OrderBookSnapshot
from agent.strategy import estimate_fair_probability


def _bundle(sentiment: float, news: float, onchain: float) -> DataBundle:
    return DataBundle(
        implied_probability=0.55,
        orderbook=OrderBookSnapshot(
            best_bid=0.54,
            best_ask=0.56,
            last_trade_price=0.55,
            bid_depth=2000,
            ask_depth=1500,
        ),
        sentiment_score=sentiment,
        news_score=news,
        onchain_flow_score=onchain,
        diagnostics=SourceDiagnostics(
            gamma_ok=True,
            clob_ok=True,
            data_api_ok=True,
            twitter_ok=True,
            news_ok=True,
            onchain_ok=True,
        ),
    )


def test_estimate_fair_probability_in_range():
    fair, conf, _ = estimate_fair_probability(_bundle(0.4, 0.2, 0.1), StrategyConfig())
    assert 0.01 <= fair <= 0.99
    assert 0.0 <= conf <= 1.0


def test_disagreement_penalizes_confidence():
    fair_a, conf_a, _ = estimate_fair_probability(_bundle(0.6, 0.6, 0.6), StrategyConfig())
    fair_b, conf_b, _ = estimate_fair_probability(_bundle(0.9, -0.9, 0.9), StrategyConfig())

    assert conf_a > conf_b
    assert fair_a != fair_b


def test_estimate_fair_probability_handles_empty_orderbook_depth():
    bundle = _bundle(0.3, 0.2, 0.1)
    bundle.orderbook.bid_depth = 0
    bundle.orderbook.ask_depth = 0

    fair, conf, _ = estimate_fair_probability(bundle, StrategyConfig())

    assert 0.01 <= fair <= 0.99
    assert 0.0 <= conf <= 1.0


def test_lexicon_sentiment_detects_positive_and_negative():
    client = PolymarketDataClient(api_cfg=APIConfig())
    positive = client._lexicon_sentiment(["Market looks bullish and strong, big win expected"])
    negative = client._lexicon_sentiment(["This outcome looks bearish and weak, likely lose"])

    assert positive > 0
    assert negative < 0
