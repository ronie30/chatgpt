from agent.config import APIConfig, StrategyConfig
from agent.data_sources import DataBundle, PolymarketDataClient, SourceDiagnostics
from agent.models import OrderBookSnapshot
from agent.strategy import estimate_fair_probability


def test_estimate_fair_probability_in_range():
    data = DataBundle(
        implied_probability=0.55,
        orderbook=OrderBookSnapshot(
            best_bid=0.54,
            best_ask=0.56,
            last_trade_price=0.55,
            bid_depth=2000,
            ask_depth=1500,
        ),
        sentiment_score=0.4,
        news_score=0.2,
        onchain_flow_score=0.1,
        diagnostics=SourceDiagnostics(
            gamma_ok=True,
            clob_ok=True,
            data_api_ok=True,
            twitter_ok=True,
            news_ok=True,
            onchain_ok=True,
        ),
    )
    fair, conf, _ = estimate_fair_probability(data, StrategyConfig())

    assert 0.01 <= fair <= 0.99
    assert 0.0 <= conf <= 1.0


def test_lexicon_sentiment_detects_positive_and_negative():
    client = PolymarketDataClient(api_cfg=APIConfig())
    positive = client._lexicon_sentiment(["Market looks bullish and strong, big win expected"])
    negative = client._lexicon_sentiment(["This outcome looks bearish and weak, likely lose"])

    assert positive > 0
    assert negative < 0
