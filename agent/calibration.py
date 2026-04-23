from dataclasses import dataclass
import math


def _clip_probability(value: float) -> float:
    return max(1e-6, min(1 - 1e-6, value))


def _sigmoid(value: float) -> float:
    if value >= 30:
        return 1.0
    if value <= -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-value))


@dataclass
class PlattScaler:
    slope: float = 1.0
    intercept: float = 0.0

    def predict(self, probability: float) -> float:
        logit = math.log(_clip_probability(probability) / (1 - _clip_probability(probability)))
        return _clip_probability(_sigmoid(self.slope * logit + self.intercept))


@dataclass
class RegimeCalibrator:
    low_vol: PlattScaler
    mid_vol: PlattScaler
    high_vol: PlattScaler

    def calibrate(self, regime_label: str, probability: float) -> float:
        if regime_label == "LOW_VOL":
            return self.low_vol.predict(probability)
        if regime_label == "MID_VOL":
            return self.mid_vol.predict(probability)
        return self.high_vol.predict(probability)


class _LogisticCalibratorTrainer:
    def __init__(self, epochs: int = 250, learning_rate: float = 0.05) -> None:
        self.epochs = epochs
        self.learning_rate = learning_rate

    def fit(self, probabilities: list[float], outcomes: list[int]) -> PlattScaler:
        if len(probabilities) < 8:
            return PlattScaler()
        positives = sum(outcomes)
        if positives == 0 or positives == len(outcomes):
            return PlattScaler()

        logits = [math.log(_clip_probability(p) / (1 - _clip_probability(p))) for p in probabilities]
        slope = 1.0
        intercept = 0.0

        for _ in range(self.epochs):
            grad_slope = 0.0
            grad_intercept = 0.0
            n = len(logits)
            for logit, y in zip(logits, outcomes):
                pred = _sigmoid((slope * logit) + intercept)
                err = pred - y
                grad_slope += err * logit
                grad_intercept += err

            slope -= self.learning_rate * (grad_slope / n)
            intercept -= self.learning_rate * (grad_intercept / n)

        return PlattScaler(slope=slope, intercept=intercept)


def fit_regime_calibrator(
    regime_labels: list[str],
    raw_probabilities: list[float],
    outcomes: list[int],
) -> RegimeCalibrator:
    trainer = _LogisticCalibratorTrainer()

    buckets: dict[str, tuple[list[float], list[int]]] = {
        "LOW_VOL": ([], []),
        "MID_VOL": ([], []),
        "HIGH_VOL": ([], []),
    }

    for label, prob, outcome in zip(regime_labels, raw_probabilities, outcomes):
        probs, ys = buckets.get(label, buckets["HIGH_VOL"])
        probs.append(prob)
        ys.append(outcome)

    low = trainer.fit(*buckets["LOW_VOL"])
    mid = trainer.fit(*buckets["MID_VOL"])
    high = trainer.fit(*buckets["HIGH_VOL"])

    return RegimeCalibrator(low_vol=low, mid_vol=mid, high_vol=high)
