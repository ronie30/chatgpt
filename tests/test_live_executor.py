from pathlib import Path

from agent.config import APIConfig
from agent.execution import LiveCLOBExecutor, OrderRequest, PaperExecutor
from agent.order_ledger import CSVOrderLedger


def test_live_executor_disabled_without_api_key(tmp_path: Path):
    ledger = CSVOrderLedger(path=str(tmp_path / "ledger.csv"))
    executor = LiveCLOBExecutor(api_cfg=APIConfig(polymarket_api_key=None), ledger=ledger)
    result = executor.submit_order(
        OrderRequest(market_id="m1", side="BUY", price=0.5, size_usd=10, idempotency_key="x")
    )

    assert result.status == "LIVE_DISABLED"
    assert result.accepted is False


def test_paper_executor_writes_ledger(tmp_path: Path):
    path = tmp_path / "ledger.csv"
    ledger = CSVOrderLedger(path=str(path))
    executor = PaperExecutor(max_notional_usd=100, ledger=ledger)

    result = executor.submit_order(
        OrderRequest(market_id="m1", side="BUY", price=0.5, size_usd=10, idempotency_key="x")
    )
    assert result.accepted is True

    content = path.read_text(encoding="utf-8")
    assert "timestamp_utc" in content
    assert "m1" in content
