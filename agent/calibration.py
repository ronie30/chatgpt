from dataclasses import dataclass

from .math_utils import clip_probability, logit, sigmoid


@dataclass
class PlattScaler:
    slope: float = 1.0
    intercept: float = 0.0

    def predict(self, probability: float) -> float:
        probability_logit = logit(probability)
        calibrated = sigmoid(self.slope * probability_logit + self.intercept)
        return clip_probability(calibrated)


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

        logits = [logit(p) for p in probabilities]
        slope = 1.0
        intercept = 0.0

        for _ in range(self.epochs):
            grad_slope = 0.0
            grad_intercept = 0.0
            n = len(logits)
            for logit_value, outcome in zip(logits, outcomes):
                prediction = sigmoid((slope * logit_value) + intercept)
                error = prediction - outcome
                grad_slope += error * logit_value
                grad_intercept += error

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

    for label, probability, outcome in zip(regime_labels, raw_probabilities, outcomes):
        probs, labels = buckets.get(label, buckets["HIGH_VOL"])
        probs.append(probability)
        labels.append(outcome)

    low = trainer.fit(*buckets["LOW_VOL"])
    mid = trainer.fit(*buckets["MID_VOL"])
    high = trainer.fit(*buckets["HIGH_VOL"])

    return RegimeCalibrator(low_vol=low, mid_vol=mid, high_vol=high)
