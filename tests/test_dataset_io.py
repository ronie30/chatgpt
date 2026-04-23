from pathlib import Path

from agent.dataset_io import load_labeled_bundles


def test_load_labeled_bundles_reads_rows():
    csv_path = Path(__file__).parent / "data" / "backtest_sample.csv"
    rows = load_labeled_bundles(str(csv_path))

    assert len(rows) == 5
    bundle, outcome = rows[0]
    assert 0.0 < bundle.implied_probability < 1.0
    assert outcome in {0, 1}
