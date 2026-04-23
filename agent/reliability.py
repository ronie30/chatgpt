from dataclasses import dataclass

from .config import AgentConfig
from .dataset_io import load_labeled_bundles
from .metrics import brier_score, calibration_curve, log_loss
from .strategy import estimate_fair_probability


@dataclass
class ReliabilityReport:
    rows: int
    brier: float
    logloss: float
    hit_rate: float
    calibration_gap: float
    prior_window_brier: float
    recent_window_brier: float
    brier_drift: float
    prior_window_hit_rate: float
    recent_window_hit_rate: float
    hit_rate_drift: float


def _ece(predictions: list[float], outcomes: list[int], bins: int = 10) -> float:
    curve = calibration_curve(predictions, outcomes, bins=bins)
    total = len(predictions)
    if total == 0:
        return 0.0

    error = 0.0
    for bucket in curve:
        if bucket.count == 0:
            continue
        error += abs(bucket.avg_predicted - bucket.observed_rate) * (bucket.count / total)
    return error


def _directional_hit_rate(predictions: list[float], implied_probabilities: list[float], outcomes: list[int]) -> float:
    if not predictions:
        return 0.0

    wins = 0
    for pred, implied, outcome in zip(predictions, implied_probabilities, outcomes):
        direction = 1 if (pred - implied) > 0 else 0
        wins += int(direction == outcome)
    return wins / len(predictions)


def run_reliability_report(
    csv_path: str,
    config: AgentConfig | None = None,
    window_size: int = 20,
) -> ReliabilityReport:
    cfg = config or AgentConfig()
    rows = load_labeled_bundles(csv_path)

    predictions: list[float] = []
    implied_probabilities: list[float] = []
    outcomes: list[int] = []
    for bundle, outcome in rows:
        fair_probability, _, _ = estimate_fair_probability(bundle, cfg.strategy)
        predictions.append(fair_probability)
        implied_probabilities.append(bundle.implied_probability)
        outcomes.append(outcome)

    n = len(predictions)
    if n == 0:
        return ReliabilityReport(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    hit_rate = _directional_hit_rate(predictions, implied_probabilities, outcomes)
    calibration_gap = _ece(predictions, outcomes, bins=10)

    window = max(2, min(window_size, n))
    prior_start = max(0, n - (2 * window))
    prior_end = max(0, n - window)

    prior_preds = predictions[prior_start:prior_end] if prior_end > prior_start else predictions[:window]
    prior_implied = implied_probabilities[prior_start:prior_end] if prior_end > prior_start else implied_probabilities[:window]
    prior_outcomes = outcomes[prior_start:prior_end] if prior_end > prior_start else outcomes[:window]

    recent_preds = predictions[-window:]
    recent_implied = implied_probabilities[-window:]
    recent_outcomes = outcomes[-window:]

    prior_brier = brier_score(prior_preds, prior_outcomes)
    recent_brier = brier_score(recent_preds, recent_outcomes)
    prior_hit = _directional_hit_rate(prior_preds, prior_implied, prior_outcomes)
    recent_hit = _directional_hit_rate(recent_preds, recent_implied, recent_outcomes)

    return ReliabilityReport(
        rows=n,
        brier=brier_score(predictions, outcomes),
        logloss=log_loss(predictions, outcomes),
        hit_rate=hit_rate,
        calibration_gap=calibration_gap,
        prior_window_brier=prior_brier,
        recent_window_brier=recent_brier,
        brier_drift=recent_brier - prior_brier,
        prior_window_hit_rate=prior_hit,
        recent_window_hit_rate=recent_hit,
        hit_rate_drift=recent_hit - prior_hit,
    )
