"""High-level orchestration for decision and execution."""
from dataclasses import dataclass

from .config import AgentConfig
from .data_sources import PolymarketDataClient
from .execution import (
    ExecutionResult,
    OrderExecutor,
    PaperExecutor,
    ResilientExecutor,
    decision_to_order_request,
)
from .models import TradeDecision
from .observability import NullObserver
from .quality import DataQualityGuard
from .regime import detect_regime
from .risk import kelly_size_usd
from .strategy import estimate_fair_probability


@dataclass
class DecisionExecution:
    decision: TradeDecision
    execution: ExecutionResult | None


class TradingAgent:
    def __init__(
        self,
        config: AgentConfig | None = None,
        bankroll_usd: float = 1000.0,
        executor: OrderExecutor | None = None,
        observer=None,
    ):
        self.cfg = config or AgentConfig()
        self.client = PolymarketDataClient(api_cfg=self.cfg.api)
        self.bankroll_usd = bankroll_usd
        self.executor = executor or ResilientExecutor(
            inner=PaperExecutor(max_notional_usd=self.cfg.risk.max_position_usd),
            max_retries=2,
            retry_backoff_sec=0.05,
            failure_threshold=3,
            circuit_cooldown_sec=5.0,
        )
        self.quality_guard = DataQualityGuard(config=self.cfg.quality)
        self.observer = observer or NullObserver()

    def evaluate_market(self, market_id: str) -> TradeDecision:
        data = self.client.fetch_data_bundle(market_id)
        fair_probability, confidence, features = estimate_fair_probability(data, self.cfg.strategy)
        regime = detect_regime(data, features, config=self.cfg.regime)
        quality = self.quality_guard.assess(market_id, data)

        edge = fair_probability - data.implied_probability
        expected_value_bps = edge * 10_000
        effective_confidence = min(
            1.0,
            confidence * (0.75 + 0.25 * features.source_health) * regime.confidence_multiplier * quality.quality_score,
        )

        if quality.quality_score < 0.50:
            self.observer.inc("quality_gate_holds")
            return TradeDecision(
                market_id=market_id,
                signal="HOLD",
                target_price=data.implied_probability,
                edge=edge,
                size_usd=0.0,
                confidence=effective_confidence,
                expected_value_bps=expected_value_bps,
                source_health=features.source_health,
                regime=regime.label,
                rationale=(
                    "Data quality rendah; anomali terdeteksi. "
                    f"anomalies={';'.join(quality.anomalies)}"
                ),
            )

        if features.source_health < self.cfg.risk.min_source_health:
            self.observer.inc("source_health_holds")
            return TradeDecision(
                market_id=market_id,
                signal="HOLD",
                target_price=data.implied_probability,
                edge=edge,
                size_usd=0.0,
                confidence=effective_confidence,
                expected_value_bps=expected_value_bps,
                source_health=features.source_health,
                regime=regime.label,
                rationale="Source health terlalu rendah; data tidak cukup terpercaya untuk eksekusi.",
            )

        if features.liquidity_score < self.cfg.risk.min_liquidity_score:
            self.observer.inc("liquidity_holds")
            return TradeDecision(
                market_id=market_id,
                signal="HOLD",
                target_price=data.implied_probability,
                edge=edge,
                size_usd=0.0,
                confidence=effective_confidence,
                expected_value_bps=expected_value_bps,
                source_health=features.source_health,
                regime=regime.label,
                rationale="Likuiditas market tidak memenuhi syarat minimum.",
            )

        if (
            effective_confidence < self.cfg.risk.min_confidence
            or abs(edge) < self.cfg.strategy.edge_threshold
            or abs(expected_value_bps) < self.cfg.risk.min_expected_value_bps
        ):
            self.observer.inc("threshold_holds")
            return TradeDecision(
                market_id=market_id,
                signal="HOLD",
                target_price=data.implied_probability,
                edge=edge,
                size_usd=0.0,
                confidence=effective_confidence,
                expected_value_bps=expected_value_bps,
                source_health=features.source_health,
                regime=regime.label,
                rationale=(
                    "Sinyal belum memenuhi quality gate. "
                    f"ev_bps={expected_value_bps:.1f}, conf={effective_confidence:.2f}, "
                    f"liq={features.liquidity_score:.2f}, regime={regime.label}, q={quality.quality_score:.2f}"
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
        size *= regime.risk_multiplier

        self.observer.inc("signals_generated")
        return TradeDecision(
            market_id=market_id,
            signal=signal,
            target_price=fair_probability,
            edge=edge,
            size_usd=size,
            confidence=effective_confidence,
            expected_value_bps=expected_value_bps,
            source_health=features.source_health,
            regime=regime.label,
            rationale=(
                f"Signal {signal}: fair_prob={fair_probability:.3f}, implied={data.implied_probability:.3f}, "
                f"ev_bps={expected_value_bps:.1f}, conf={effective_confidence:.3f}, "
                f"liq={features.liquidity_score:.2f}, regime={regime.label}, q={quality.quality_score:.2f}."
            ),
        )

    def execute_market(self, market_id: str) -> DecisionExecution:
        decision = self.evaluate_market(market_id)
        request = decision_to_order_request(decision)
        if request is None:
            return DecisionExecution(decision=decision, execution=None)
        execution = self.executor.submit_order(request)
        return DecisionExecution(decision=decision, execution=execution)
