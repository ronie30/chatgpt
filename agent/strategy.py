import math

from .config import StrategyConfig
from .data_sources import DataBundle
from .feature_engineering import binary_entropy, build_features
from .models import MarketFeatures


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _sigmoid(x: float) -> float:
    if x > 10:
        return 1.0
    if x < -10:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _logit(probability: float) -> float:
    p = _clip(probability, 1e-6, 1 - 1e-6)
    return math.log(p / (1 - p))


def _disagreement(sentiment: float, news: float, onchain: float) -> float:
    return (
        abs(sentiment - news)
        + abs(news - onchain)
        + abs(sentiment - onchain)
    ) / 6.0


def estimate_fair_probability(data: DataBundle, cfg: StrategyConfig) -> tuple[float, float, MarketFeatures]:
    total_depth = data.orderbook.bid_depth + data.orderbook.ask_depth
    orderflow_signal = (
        (data.orderbook.bid_depth - data.orderbook.ask_depth) / total_depth
        if total_depth > 0
        else 0.0
    )

    signal_strength = (
        cfg.sentiment_weight * data.sentiment_score
        + cfg.news_weight * data.news_score
        + cfg.onchain_weight * data.onchain_flow_score
        + cfg.orderflow_weight * orderflow_signal
    )

    prior_logit = _logit(data.implied_probability)
    posterior_logit = prior_logit * cfg.prior_strength + signal_strength * (1 - cfg.prior_strength)
    base_probability = _sigmoid(posterior_logit)

    disagreement_penalty = _disagreement(data.sentiment_score, data.news_score, data.onchain_flow_score)
    entropy_penalty = binary_entropy(base_probability)

    adjusted_probability = base_probability - (
        cfg.disagreement_penalty_weight * disagreement_penalty * 0.08
        + cfg.entropy_penalty_weight * entropy_penalty * 0.05
    )
    fair_probability = _clip(adjusted_probability, 0.01, 0.99)

    source_health = sum(
        int(flag)
        for flag in [
            data.diagnostics.gamma_ok,
            data.diagnostics.clob_ok,
            data.diagnostics.data_api_ok,
            data.diagnostics.twitter_ok,
            data.diagnostics.news_ok,
            data.diagnostics.onchain_ok,
        ]
    ) / 6.0

    consensus = 1.0 - disagreement_penalty
    confidence = _clip((0.45 * consensus) + (0.30 * abs(orderflow_signal)) + (0.25 * source_health), 0.0, 1.0)

    features = build_features(
        market_id="unknown",
        data=data,
        fair_probability=fair_probability,
        confidence=confidence,
        disagreement_penalty=disagreement_penalty,
        source_health=source_health,
    )
    return fair_probability, confidence, features
