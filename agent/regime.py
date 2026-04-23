from dataclasses import dataclass

from .data_sources import DataBundle
from .models import MarketFeatures


@dataclass
class RegimeState:
    label: str
    volatility_score: float
    risk_multiplier: float
    confidence_multiplier: float


def detect_regime(data: DataBundle, features: MarketFeatures) -> RegimeState:
    spread = max(0.0, data.orderbook.best_ask - data.orderbook.best_bid)
    dispersion = (
        abs(features.sentiment_score - features.news_score)
        + abs(features.news_score - features.onchain_flow_score)
        + abs(features.sentiment_score - features.onchain_flow_score)
    ) / 3.0

    volatility_score = min(1.0, (spread / 0.05) * 0.55 + dispersion * 0.45)

    if volatility_score >= 0.70:
        return RegimeState(
            label="HIGH_VOL",
            volatility_score=volatility_score,
            risk_multiplier=0.45,
            confidence_multiplier=0.85,
        )
    if volatility_score >= 0.40:
        return RegimeState(
            label="MID_VOL",
            volatility_score=volatility_score,
            risk_multiplier=0.70,
            confidence_multiplier=0.93,
        )
    return RegimeState(
        label="LOW_VOL",
        volatility_score=volatility_score,
        risk_multiplier=1.0,
        confidence_multiplier=1.0,
    )
