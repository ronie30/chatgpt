from pathlib import Path

from agent.tuning import tune_thresholds


def test_tune_thresholds_returns_valid_result():
    csv_path = Path(__file__).parent / "data" / "backtest_sample.csv"
    result = tune_thresholds(str(csv_path))

    assert result.evaluated > 0
    assert 0.0 <= result.best_min_confidence <= 1.0
    assert result.best_edge_threshold > 0
    assert result.best_min_ev_bps > 0
    assert 0.0 <= result.win_rate <= 1.0
