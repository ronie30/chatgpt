from dataclasses import dataclass

from .config import RegimeConfig
from .data_sources import DataBundle
from .math_utils import clip
from .models import MarketFeatures


@dataclass
class RegimeState:
    label: str
    volatility_score: float
    risk_multiplier: float
    confidence_multiplier: float


def detect_regime(
    data: DataBundle,
    features: MarketFeatures,
    config: RegimeConfig | None = None,
) -> RegimeState:
    cfg = config or RegimeConfig()

    spread = max(0.0, data.orderbook.best_ask - data.orderbook.best_bid)
    dispersion = (
        abs(features.sentiment_score - features.news_score)
        + abs(features.news_score - features.onchain_flow_score)
        + abs(features.sentiment_score - features.onchain_flow_score)
    ) / 3.0

    spread_term = spread / max(cfg.spread_norm, 1e-6)
    volatility_score = clip(
        (spread_term * cfg.spread_weight) + (dispersion * cfg.dispersion_weight),
        0.0,
        1.0,
    )

    if volatility_score >= cfg.high_vol_threshold:
        return RegimeState(
            label="HIGH_VOL",
            volatility_score=volatility_score,
            risk_multiplier=cfg.high_vol_risk_multiplier,
            confidence_multiplier=cfg.high_vol_confidence_multiplier,
        )
    if volatility_score >= cfg.mid_vol_threshold:
        return RegimeState(
            label="MID_VOL",
            volatility_score=volatility_score,
            risk_multiplier=cfg.mid_vol_risk_multiplier,
            confidence_multiplier=cfg.mid_vol_confidence_multiplier,
        )
    return RegimeState(
        label="LOW_VOL",
        volatility_score=volatility_score,
        risk_multiplier=cfg.low_vol_risk_multiplier,
        confidence_multiplier=cfg.low_vol_confidence_multiplier,
    )
