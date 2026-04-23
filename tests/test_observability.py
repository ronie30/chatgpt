from pathlib import Path

from agent.observability import AlertManager, AlertRule, ObservabilityStack


def test_observability_logs_and_metrics(tmp_path: Path):
    stack = ObservabilityStack(logger_path=str(tmp_path / "events.jsonl"))
    stack.inc("execution_failures", 2)
    stack.observe("latency_ms", 123)
    stack.log("test_event", {"ok": True})

    snap = stack.metrics.snapshot()
    assert snap["counters"]["execution_failures"] == 2
    assert snap["histograms"]["latency_ms"]["count"] == 1


def test_alert_manager_triggers():
    manager = AlertManager(rules=[AlertRule("x", 1, "gt", "x high")])
    alerts = manager.evaluate({"x": 2})
    assert len(alerts) == 1
