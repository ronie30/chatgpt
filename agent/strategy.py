from .config import StrategyConfig
from .data_sources import DataBundle
from .feature_engineering import build_features
from .models import MarketFeatures


def _sigmoid(x: float) -> float:
    if x > 10:
        return 1.0
    if x < -10:
        return 0.0
    import math

    return 1.0 / (1.0 + math.exp(-x))


def estimate_fair_probability(data: DataBundle, cfg: StrategyConfig) -> tuple[float, float, MarketFeatures]:
    # Ensemble score dari sumber heterogen
    orderflow_signal = (data.orderbook.bid_depth - data.orderbook.ask_depth) / (
        data.orderbook.bid_depth + data.orderbook.ask_depth
    )
    raw_score = (
        cfg.sentiment_weight * data.sentiment_score
        + cfg.news_weight * data.news_score
        + cfg.onchain_weight * data.onchain_flow_score
        + cfg.orderflow_weight * orderflow_signal
    )

    # Fair probability dipusatkan pada implied probability + adjustment score
    adjustment = 0.18 * (2 * _sigmoid(raw_score) - 1)
    fair_probability = data.implied_probability + adjustment

    # Confidence: konsensus antar sinyal + liquidity proxy
    consensus = 1.0 - (
        abs(data.sentiment_score - data.news_score)
        + abs(data.news_score - data.onchain_flow_score)
        + abs(data.sentiment_score - data.onchain_flow_score)
    ) / 6.0
    confidence = max(0.0, min(1.0, 0.65 * consensus + 0.35 * abs(orderflow_signal)))

    features = build_features(
        market_id="unknown",
        data=data,
        fair_probability=fair_probability,
        confidence=confidence,
    )
    return fair_probability, confidence, features
