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
        fair_probability, confidence, _ = estimate_fair_probability(data, self.cfg.strategy)

        edge = fair_probability - data.implied_probability
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
        ) / 6

        effective_confidence = min(1.0, confidence * (0.7 + 0.3 * source_health))
        if source_health < 0.34:
            return TradeDecision(
                market_id=market_id,
                signal="HOLD",
                target_price=data.implied_probability,
                edge=edge,
                size_usd=0.0,
                confidence=effective_confidence,
                rationale="Source health terlalu rendah; data tidak cukup terpercaya untuk eksekusi.",
            )

        if effective_confidence < self.cfg.risk.min_confidence or abs(edge) < self.cfg.strategy.edge_threshold:
            return TradeDecision(
                market_id=market_id,
                signal="HOLD",
                target_price=data.implied_probability,
                edge=edge,
                size_usd=0.0,
                confidence=effective_confidence,
                rationale=(
                    "Confidence/edge belum memenuhi threshold. "
                    f"source_health={source_health:.2f}, raw_conf={confidence:.2f}"
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
            rationale=(
                f"Signal {signal}: fair_prob={fair_probability:.3f}, implied={data.implied_probability:.3f}, "
                f"raw_conf={confidence:.3f}, source_health={source_health:.2f}."
            ),
        )
