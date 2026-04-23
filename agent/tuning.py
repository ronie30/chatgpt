from dataclasses import dataclass
from itertools import product

from .config import AgentConfig
from .data_sources import DataBundle
from .dataset_io import load_labeled_bundles
from .strategy import estimate_fair_probability


@dataclass
class TuningResult:
    evaluated: int
    best_min_confidence: float
    best_edge_threshold: float
    best_min_ev_bps: float
    best_score: float
    trades: int
    win_rate: float


def tune_thresholds_rows(
    rows: list[tuple[DataBundle, int]],
    config: AgentConfig | None = None,
    min_conf_grid: list[float] | None = None,
    edge_grid: list[float] | None = None,
    min_ev_grid: list[float] | None = None,
) -> TuningResult:
    cfg = config or AgentConfig()
    min_conf_grid = min_conf_grid or [0.50, 0.55, 0.60, 0.65, 0.70]
    edge_grid = edge_grid or [0.01, 0.02, 0.03, 0.04]
    min_ev_grid = min_ev_grid or [20, 40, 60, 80]

    best_score = float("-inf")
    best = (cfg.risk.min_confidence, cfg.strategy.edge_threshold, cfg.risk.min_expected_value_bps, 0, 0.0)

    for min_conf, edge_threshold, min_ev in product(min_conf_grid, edge_grid, min_ev_grid):
        pnl = 0.0
        trades = 0
        wins = 0

        for bundle, outcome in rows:
            fair, confidence, features = estimate_fair_probability(bundle, cfg.strategy)
            edge = fair - bundle.implied_probability
            ev_bps = edge * 10_000

            if features.source_health < 0.34 or features.liquidity_score < cfg.risk.min_liquidity_score:
                continue
            if confidence < min_conf or abs(edge) < edge_threshold or abs(ev_bps) < min_ev:
                continue

            trades += 1
            direction = 1 if edge > 0 else 0
            is_win = int(direction == outcome)
            wins += is_win
            pnl += ev_bps if is_win else -abs(ev_bps)

        win_rate = (wins / trades) if trades else 0.0
        score = pnl + (win_rate * 2000) - (50 if trades == 0 else 0)

        if score > best_score:
            best_score = score
            best = (min_conf, edge_threshold, min_ev, trades, win_rate)

    return TuningResult(
        evaluated=len(min_conf_grid) * len(edge_grid) * len(min_ev_grid),
        best_min_confidence=best[0],
        best_edge_threshold=best[1],
        best_min_ev_bps=best[2],
        best_score=best_score,
        trades=best[3],
        win_rate=best[4],
    )


def tune_thresholds(
    csv_path: str,
    config: AgentConfig | None = None,
    min_conf_grid: list[float] | None = None,
    edge_grid: list[float] | None = None,
    min_ev_grid: list[float] | None = None,
) -> TuningResult:
    rows = load_labeled_bundles(csv_path)
    return tune_thresholds_rows(rows, config, min_conf_grid, edge_grid, min_ev_grid)
