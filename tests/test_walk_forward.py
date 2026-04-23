from pathlib import Path

from agent.walk_forward import run_walk_forward


def test_run_walk_forward_returns_summary_and_folds():
    csv_path = Path(__file__).parent / "data" / "backtest_sample.csv"
    summary, folds = run_walk_forward(str(csv_path), train_size=3, test_size=1)

    assert summary.folds >= 1
    assert summary.total_test_rows >= 1
    assert len(folds) == summary.folds
    assert 0.0 <= summary.avg_win_rate <= 1.0
