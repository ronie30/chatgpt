from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock


class NullObserver:
    def log(self, event: str, payload: dict) -> None:
        return

    def inc(self, metric: str, value: float = 1.0) -> None:
        return

    def observe(self, metric: str, value: float) -> None:
        return


class MetricsRegistry:
    def __init__(self):
        self._counters: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._lock = Lock()

    def inc(self, metric: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[metric] = self._counters.get(metric, 0.0) + value

    def observe(self, metric: str, value: float) -> None:
        with self._lock:
            self._histograms.setdefault(metric, []).append(value)

    def snapshot(self) -> dict:
        with self._lock:
            hist = {
                k: {
                    "count": len(v),
                    "min": min(v) if v else 0.0,
                    "max": max(v) if v else 0.0,
                    "avg": (sum(v) / len(v)) if v else 0.0,
                }
                for k, v in self._histograms.items()
            }
            return {"counters": dict(self._counters), "histograms": hist}


class JSONLogger:
    def __init__(self, path: str = "artifacts/agent_events.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def log(self, event: str, payload: dict) -> None:
        row = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload,
        }
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")


@dataclass
class AlertRule:
    metric: str
    threshold: float
    comparison: str  # "gt" / "lt"
    message: str


class AlertManager:
    def __init__(self, rules: list[AlertRule] | None = None):
        self.rules = rules or [
            AlertRule("execution_failures", 5, "gt", "Execution failures terlalu tinggi"),
            AlertRule("quality_gate_holds", 20, "gt", "Quality gate HOLD meningkat tajam"),
        ]

    def evaluate(self, counters: dict[str, float]) -> list[str]:
        alerts: list[str] = []
        for r in self.rules:
            value = counters.get(r.metric, 0.0)
            if r.comparison == "gt" and value > r.threshold:
                alerts.append(f"{r.message}: {value} > {r.threshold}")
            if r.comparison == "lt" and value < r.threshold:
                alerts.append(f"{r.message}: {value} < {r.threshold}")
        return alerts


class ObservabilityStack:
    def __init__(self, logger_path: str = "artifacts/agent_events.jsonl"):
        self.metrics = MetricsRegistry()
        self.logger = JSONLogger(path=logger_path)
        self.alerts = AlertManager()

    def log(self, event: str, payload: dict) -> None:
        self.logger.log(event, payload)

    def inc(self, metric: str, value: float = 1.0) -> None:
        self.metrics.inc(metric, value)

    def observe(self, metric: str, value: float) -> None:
        self.metrics.observe(metric, value)

    def alert_messages(self) -> list[str]:
        snap = self.metrics.snapshot()
        return self.alerts.evaluate(snap.get("counters", {}))
