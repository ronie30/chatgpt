from .config import RiskConfig


def kelly_size_usd(
    bankroll_usd: float,
    fair_probability: float,
    market_probability: float,
    confidence: float,
    risk_cfg: RiskConfig,
) -> float:
    if market_probability <= 0 or market_probability >= 1:
        return 0.0

    b = (1.0 - market_probability) / market_probability
    p = fair_probability
    q = 1.0 - p

    kelly_fraction = max(0.0, (b * p - q) / b)
    kelly_fraction = min(kelly_fraction, risk_cfg.kelly_fraction_cap)

    adjusted_fraction = kelly_fraction * confidence
    raw_size = bankroll_usd * adjusted_fraction

    return min(raw_size, risk_cfg.max_position_usd)
