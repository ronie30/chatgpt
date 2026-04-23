from pathlib import Path

from agent.backtest import run_backtest


def test_run_backtest_returns_summary_and_curve():
    csv_path = Path(__file__).parent / "data" / "backtest_sample.csv"
    summary, curve = run_backtest(str(csv_path))

    assert summary.rows == 5
    assert summary.brier >= 0
    assert summary.logloss >= 0
    assert len(curve) == 10
