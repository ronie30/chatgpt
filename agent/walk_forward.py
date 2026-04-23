from dataclasses import dataclass

from .config import AgentConfig
from .dataset_io import load_labeled_bundles
from .metrics import brier_score
from .strategy import estimate_fair_probability
from .tuning import tune_thresholds_rows


@dataclass
class FoldResult:
    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    trades: int
    win_rate: float
    avg_ev_bps: float
    brier: float


@dataclass
class WalkForwardSummary:
    folds: int
    total_test_rows: int
    total_trades: int
    avg_win_rate: float
    avg_ev_bps: float
    avg_brier: float


def run_walk_forward(
    csv_path: str,
    config: AgentConfig | None = None,
    train_size: int = 60,
    test_size: int = 20,
) -> tuple[WalkForwardSummary, list[FoldResult]]:
    cfg = config or AgentConfig()
    data = load_labeled_bundles(csv_path)

    if len(data) < (train_size + test_size):
        raise ValueError("Dataset terlalu kecil untuk walk-forward validation.")

    folds: list[FoldResult] = []
    all_briers: list[float] = []
    total_trades = 0
    total_test_rows = 0

    fold_num = 0
    start = 0
    while start + train_size + test_size <= len(data):
        fold_num += 1
        train_slice = data[start : start + train_size]
        test_slice = data[start + train_size : start + train_size + test_size]

        tuned = tune_thresholds_rows(train_slice, config=cfg)

        predictions: list[float] = []
        outcomes: list[int] = []
        trades = 0
        wins = 0
        ev_bps_sum = 0.0

        for bundle, outcome in test_slice:
            fair, confidence, features = estimate_fair_probability(bundle, cfg.strategy)
            edge = fair - bundle.implied_probability
            ev_bps = edge * 10_000

            predictions.append(fair)
            outcomes.append(outcome)

            if features.source_health < 0.34 or features.liquidity_score < cfg.risk.min_liquidity_score:
                continue
            if confidence < tuned.best_min_confidence:
                continue
            if abs(edge) < tuned.best_edge_threshold:
                continue
            if abs(ev_bps) < tuned.best_min_ev_bps:
                continue

            trades += 1
            decision = 1 if edge > 0 else 0
            if decision == outcome:
                wins += 1
                ev_bps_sum += ev_bps
            else:
                ev_bps_sum -= abs(ev_bps)

        fold_brier = brier_score(predictions, outcomes)
        all_briers.append(fold_brier)

        folds.append(
            FoldResult(
                fold=fold_num,
                train_start=start,
                train_end=start + train_size - 1,
                test_start=start + train_size,
                test_end=start + train_size + test_size - 1,
                trades=trades,
                win_rate=(wins / trades) if trades else 0.0,
                avg_ev_bps=(ev_bps_sum / trades) if trades else 0.0,
                brier=fold_brier,
            )
        )

        total_trades += trades
        total_test_rows += len(test_slice)
        start += test_size

    summary = WalkForwardSummary(
        folds=len(folds),
        total_test_rows=total_test_rows,
        total_trades=total_trades,
        avg_win_rate=sum(f.win_rate for f in folds) / len(folds) if folds else 0.0,
        avg_ev_bps=sum(f.avg_ev_bps for f in folds) / len(folds) if folds else 0.0,
        avg_brier=sum(all_briers) / len(all_briers) if all_briers else 0.0,
    )
    return summary, folds
