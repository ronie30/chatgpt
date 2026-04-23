from collections import defaultdict, deque
from dataclasses import dataclass
import math

from .data_sources import DataBundle


@dataclass
class QualityAssessment:
    quality_score: float
    anomalies: list[str]


class DataQualityGuard:
    """Simple rolling anomaly detector untuk menjaga kualitas data realtime."""

    def __init__(self, window: int = 50):
        self.window = window
        self._history: dict[str, dict[str, deque[float]]] = defaultdict(
            lambda: {
                "implied": deque(maxlen=window),
                "spread": deque(maxlen=window),
                "depth": deque(maxlen=window),
            }
        )

    def assess(self, market_id: str, data: DataBundle) -> QualityAssessment:
        spread = max(0.0, data.orderbook.best_ask - data.orderbook.best_bid)
        depth = data.orderbook.bid_depth + data.orderbook.ask_depth

        history = self._history[market_id]
        anomalies: list[str] = []

        anomalies += self._z_anomaly("implied", data.implied_probability, history["implied"], threshold=4.0)
        anomalies += self._z_anomaly("spread", spread, history["spread"], threshold=4.0)
        anomalies += self._z_anomaly("depth", depth, history["depth"], threshold=4.5)

        history["implied"].append(data.implied_probability)
        history["spread"].append(spread)
        history["depth"].append(depth)

        quality_score = max(0.0, 1.0 - 0.25 * len(anomalies))
        return QualityAssessment(quality_score=quality_score, anomalies=anomalies)

    def _z_anomaly(self, name: str, value: float, series: deque[float], threshold: float) -> list[str]:
        if len(series) < 10:
            return []

        mean = sum(series) / len(series)
        var = sum((x - mean) ** 2 for x in series) / len(series)
        std = math.sqrt(var)
        if std <= 1e-12:
            baseline = mean if abs(mean) > 1e-12 else 1.0
            rel_change = abs(value - mean) / abs(baseline)
            return [f"{name}_jump={rel_change:.2f}"] if rel_change > 0.25 else []

        z = abs((value - mean) / std)
        return [f"{name}_zscore={z:.2f}"] if z >= threshold else []
