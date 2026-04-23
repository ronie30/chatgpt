from agent.config import AgentConfig, RiskConfig, StrategyConfig
from agent.data_sources import DataBundle, SourceDiagnostics
from agent.models import OrderBookSnapshot
from agent.orchestrator import TradingAgent


class StubClient:
    def __init__(self, bundle: DataBundle):
        self.bundle = bundle

    def fetch_data_bundle(self, market_id: str) -> DataBundle:
        return self.bundle


def test_agent_holds_when_source_health_low_even_with_edge():
    bundle = DataBundle(
        implied_probability=0.40,
        orderbook=OrderBookSnapshot(
            best_bid=0.39,
            best_ask=0.41,
            last_trade_price=0.40,
            bid_depth=5000,
            ask_depth=1000,
        ),
        sentiment_score=0.9,
        news_score=0.9,
        onchain_flow_score=0.9,
        diagnostics=SourceDiagnostics(
            gamma_ok=False,
            clob_ok=False,
            data_api_ok=False,
            twitter_ok=False,
            news_ok=False,
            onchain_ok=False,
        ),
    )
    agent = TradingAgent(config=AgentConfig(), bankroll_usd=1000)
    agent.client = StubClient(bundle)

    decision = agent.evaluate_market("m1")

    assert decision.signal == "HOLD"
    assert decision.size_usd == 0.0


def test_agent_holds_when_liquidity_too_low():
    bundle = DataBundle(
        implied_probability=0.48,
        orderbook=OrderBookSnapshot(
            best_bid=0.30,
            best_ask=0.60,
            last_trade_price=0.45,
            bid_depth=50,
            ask_depth=60,
        ),
        sentiment_score=0.6,
        news_score=0.6,
        onchain_flow_score=0.6,
        diagnostics=SourceDiagnostics(
            gamma_ok=True,
            clob_ok=True,
            data_api_ok=True,
            twitter_ok=True,
            news_ok=True,
            onchain_ok=True,
        ),
    )
    agent = TradingAgent(config=AgentConfig(), bankroll_usd=1000)
    agent.client = StubClient(bundle)

    decision = agent.evaluate_market("m2")

    assert decision.signal == "HOLD"
    assert "Likuiditas" in decision.rationale


def test_agent_sell_signal_produces_nonzero_size_for_short_edge():
    bundle = DataBundle(
        implied_probability=0.85,
        orderbook=OrderBookSnapshot(
            best_bid=0.84,
            best_ask=0.86,
            last_trade_price=0.85,
            bid_depth=5000,
            ask_depth=1000,
        ),
        sentiment_score=-0.9,
        news_score=-0.9,
        onchain_flow_score=-0.9,
        diagnostics=SourceDiagnostics(
            gamma_ok=True,
            clob_ok=True,
            data_api_ok=True,
            twitter_ok=True,
            news_ok=True,
            onchain_ok=True,
        ),
    )
    cfg = AgentConfig(
        risk=RiskConfig(min_confidence=0.0, min_expected_value_bps=0.0, min_liquidity_score=0.0),
        strategy=StrategyConfig(edge_threshold=0.0),
    )
    agent = TradingAgent(config=cfg, bankroll_usd=1000)
    agent.client = StubClient(bundle)

    decision = agent.evaluate_market("m3")

    assert decision.signal == "SELL"
    assert decision.size_usd > 0.0
