from urllib.error import URLError

from agent.config import APIConfig
import agent.execution as execution
from agent.execution import LiveCLOBExecutor, OrderRequest


def test_live_executor_network_error(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise URLError("down")

    monkeypatch.setattr(execution, "urlopen", fake_urlopen)

    api_cfg = APIConfig(polymarket_api_key="dummy-key")
    executor = LiveCLOBExecutor(api_cfg=api_cfg)
    result = executor.submit_order(OrderRequest("m1", "BUY", 0.5, 10, "k"))

    assert result.status == "NETWORK_ERROR"
