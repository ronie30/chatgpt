from agent.config import AgentConfig
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
