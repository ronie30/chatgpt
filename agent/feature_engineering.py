from .data_sources import DataBundle
from .models import MarketFeatures


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _normalize_depth_ratio(bid_depth: float, ask_depth: float) -> float:
    total = bid_depth + ask_depth
    if total <= 0:
        return 0.0
    return (bid_depth - ask_depth) / total


def _liquidity_score(spread: float, depth: float) -> float:
    spread_penalty = 1.0 - _clip(spread / 0.05, 0.0, 1.0)
    depth_boost = _clip(depth / 5000.0, 0.0, 1.0)
    return 0.5 * spread_penalty + 0.5 * depth_boost


def build_features(market_id: str, data: DataBundle, fair_probability: float, confidence: float) -> MarketFeatures:
    spread = max(0.0, data.orderbook.best_ask - data.orderbook.best_bid)
    depth = data.orderbook.bid_depth + data.orderbook.ask_depth
    imbalance = _normalize_depth_ratio(data.orderbook.bid_depth, data.orderbook.ask_depth)
    liq = _liquidity_score(spread, depth)

    return MarketFeatures(
        market_id=market_id,
        implied_probability=data.implied_probability,
        fair_probability=_clip(fair_probability, 0.01, 0.99),
        sentiment_score=data.sentiment_score,
        news_score=data.news_score,
        onchain_flow_score=data.onchain_flow_score,
        orderflow_imbalance=imbalance,
        liquidity_score=liq,
        confidence=_clip(confidence, 0.0, 1.0),
    )
