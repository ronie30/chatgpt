from pathlib import Path

from agent.reliability import run_reliability_report


def test_run_reliability_report_from_sample_csv():
    csv_path = Path(__file__).parent / "data" / "backtest_sample.csv"
    report = run_reliability_report(str(csv_path), window_size=3)

    assert report.rows >= 1
    assert report.brier >= 0.0
    assert report.logloss >= 0.0
    assert 0.0 <= report.hit_rate <= 1.0
    assert 0.0 <= report.calibration_gap <= 1.0
    assert report.brier_drift == report.recent_window_brier - report.prior_window_brier
    assert report.hit_rate_drift == report.recent_window_hit_rate - report.prior_window_hit_rate
