from dataclasses import dataclass

from .config import AgentConfig
from .dataset_io import load_labeled_bundles
from .metrics import brier_score, calibration_curve, log_loss
from .strategy import estimate_fair_probability


@dataclass
class BacktestSummary:
    rows: int
    brier: float
    logloss: float
    avg_confidence: float
    avg_edge_bps: float


def run_backtest(csv_path: str, config: AgentConfig | None = None) -> tuple[BacktestSummary, list[dict[str, float]]]:
    cfg = config or AgentConfig()

    predictions: list[float] = []
    outcomes: list[int] = []
    confidences: list[float] = []
    edges_bps: list[float] = []

    for data, outcome in load_labeled_bundles(csv_path):
        fair_probability, confidence, _ = estimate_fair_probability(data, cfg.strategy)
        predictions.append(fair_probability)
        outcomes.append(outcome)
        confidences.append(confidence)
        edges_bps.append((fair_probability - data.implied_probability) * 10_000)

    summary = BacktestSummary(
        rows=len(predictions),
        brier=brier_score(predictions, outcomes),
        logloss=log_loss(predictions, outcomes),
        avg_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        avg_edge_bps=sum(edges_bps) / len(edges_bps) if edges_bps else 0.0,
    )

    curve = calibration_curve(predictions, outcomes, bins=10)
    curve_rows = [
        {
            "bin_lower": c.lower,
            "bin_upper": c.upper,
            "avg_predicted": c.avg_predicted,
            "observed_rate": c.observed_rate,
            "count": float(c.count),
        }
        for c in curve
    ]
    return summary, curve_rows
