from .config import AgentConfig
from .data_sources import PolymarketDataClient
from .models import TradeDecision
from .risk import kelly_size_usd
from .strategy import estimate_fair_probability


class TradingAgent:
    def __init__(self, config: AgentConfig | None = None, bankroll_usd: float = 1000.0):
        self.cfg = config or AgentConfig()
        self.client = PolymarketDataClient(api_cfg=self.cfg.api)
        self.bankroll_usd = bankroll_usd

    def evaluate_market(self, market_id: str) -> TradeDecision:
        data = self.client.fetch_data_bundle(market_id)
        fair_probability, confidence, features = estimate_fair_probability(data, self.cfg.strategy)

        edge = fair_probability - data.implied_probability
        expected_value_bps = edge * 10_000
        effective_confidence = min(1.0, confidence * (0.75 + 0.25 * features.source_health))

        if features.source_health < 0.34:
            return TradeDecision(
                market_id=market_id,
                signal="HOLD",
                target_price=data.implied_probability,
                edge=edge,
                size_usd=0.0,
                confidence=effective_confidence,
                expected_value_bps=expected_value_bps,
                source_health=features.source_health,
                rationale="Source health terlalu rendah; data tidak cukup terpercaya untuk eksekusi.",
            )

        if features.liquidity_score < self.cfg.risk.min_liquidity_score:
            return TradeDecision(
                market_id=market_id,
                signal="HOLD",
                target_price=data.implied_probability,
                edge=edge,
                size_usd=0.0,
                confidence=effective_confidence,
                expected_value_bps=expected_value_bps,
                source_health=features.source_health,
                rationale="Likuiditas market tidak memenuhi syarat minimum.",
            )

        if (
            effective_confidence < self.cfg.risk.min_confidence
            or abs(edge) < self.cfg.strategy.edge_threshold
            or abs(expected_value_bps) < self.cfg.risk.min_expected_value_bps
        ):
            return TradeDecision(
                market_id=market_id,
                signal="HOLD",
                target_price=data.implied_probability,
                edge=edge,
                size_usd=0.0,
                confidence=effective_confidence,
                expected_value_bps=expected_value_bps,
                source_health=features.source_health,
                rationale=(
                    "Sinyal belum memenuhi quality gate. "
                    f"ev_bps={expected_value_bps:.1f}, conf={effective_confidence:.2f}, liq={features.liquidity_score:.2f}"
                ),
            )

        signal = "BUY" if edge > 0 else "SELL"
        size = kelly_size_usd(
            bankroll_usd=self.bankroll_usd,
            fair_probability=fair_probability,
            market_probability=data.implied_probability,
            confidence=effective_confidence,
            risk_cfg=self.cfg.risk,
        )

        return TradeDecision(
            market_id=market_id,
            signal=signal,
            target_price=fair_probability,
            edge=edge,
            size_usd=size,
            confidence=effective_confidence,
            expected_value_bps=expected_value_bps,
            source_health=features.source_health,
            rationale=(
                f"Signal {signal}: fair_prob={fair_probability:.3f}, implied={data.implied_probability:.3f}, "
                f"ev_bps={expected_value_bps:.1f}, conf={effective_confidence:.3f}, liq={features.liquidity_score:.2f}."
            ),
        )
