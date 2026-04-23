from dataclasses import dataclass
import math


@dataclass
class CalibrationBin:
    lower: float
    upper: float
    avg_predicted: float
    observed_rate: float
    count: int


def brier_score(predictions: list[float], outcomes: list[int]) -> float:
    if not predictions or len(predictions) != len(outcomes):
        return 0.0
    return sum((p - y) ** 2 for p, y in zip(predictions, outcomes)) / len(predictions)


def log_loss(predictions: list[float], outcomes: list[int]) -> float:
    if not predictions or len(predictions) != len(outcomes):
        return 0.0

    def clip(p: float) -> float:
        return max(1e-8, min(1 - 1e-8, p))

    total = 0.0
    for p, y in zip(predictions, outcomes):
        cp = clip(p)
        total += -(y * math.log(cp) + (1 - y) * math.log(1 - cp))
    return total / len(predictions)


def calibration_curve(predictions: list[float], outcomes: list[int], bins: int = 10) -> list[CalibrationBin]:
    if not predictions or len(predictions) != len(outcomes):
        return []

    bins = max(2, bins)
    result: list[CalibrationBin] = []
    for i in range(bins):
        lo = i / bins
        hi = (i + 1) / bins
        indices = [j for j, p in enumerate(predictions) if (lo <= p < hi) or (i == bins - 1 and p == 1.0)]
        if not indices:
            result.append(CalibrationBin(lo, hi, 0.0, 0.0, 0))
            continue

        bucket_preds = [predictions[j] for j in indices]
        bucket_outcomes = [outcomes[j] for j in indices]
        result.append(
            CalibrationBin(
                lower=lo,
                upper=hi,
                avg_predicted=sum(bucket_preds) / len(bucket_preds),
                observed_rate=sum(bucket_outcomes) / len(bucket_outcomes),
                count=len(indices),
            )
        )
    return result
