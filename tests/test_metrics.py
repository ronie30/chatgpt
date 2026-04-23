from agent.metrics import brier_score, calibration_curve, log_loss


def test_metrics_non_negative():
    preds = [0.1, 0.8, 0.7, 0.4]
    outcomes = [0, 1, 1, 0]

    assert brier_score(preds, outcomes) >= 0.0
    assert log_loss(preds, outcomes) >= 0.0


def test_calibration_curve_bin_count():
    preds = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
    outcomes = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1]

    bins = calibration_curve(preds, outcomes, bins=10)
    assert len(bins) == 10
    assert sum(b.count for b in bins) == len(preds)
