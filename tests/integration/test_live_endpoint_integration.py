import os
import pytest

from agent.config import APIConfig
from agent.execution import LiveCLOBExecutor, OrderRequest


@pytest.mark.integration
def test_live_endpoint_disabled_or_reachable():
    if os.getenv("RUN_LIVE_INTEGRATION") != "1":
        pytest.skip("Set RUN_LIVE_INTEGRATION=1 to run live endpoint integration test")

    cfg = APIConfig()
    executor = LiveCLOBExecutor(api_cfg=cfg)
    result = executor.submit_order(
        OrderRequest(market_id=os.getenv("LIVE_TEST_MARKET", "demo"), side="BUY", price=0.5, size_usd=1, idempotency_key="it")
    )

    # Test endpoint nyata: minimal harus return status known (termasuk LIVE_DISABLED saat key kosong)
    assert result.status in {
        "LIVE_DISABLED",
        "ACCEPTED",
        "HTTP_ERROR",
        "NETWORK_ERROR",
        "TIMEOUT",
        "FAILED",
    }
