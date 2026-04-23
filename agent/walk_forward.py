from dataclasses import dataclass
import csv

from .config import AgentConfig
from .data_sources import DataBundle, SourceDiagnostics
from .metrics import brier_score
from .models import OrderBookSnapshot
from .strategy import estimate_fair_probability
from .tuning import tune_thresholds


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


def _to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "ok"}


def _read_dataset(csv_path: str) -> list[tuple[DataBundle, int]]:
    rows: list[tuple[DataBundle, int]] = []
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                (
                    DataBundle(
                        implied_probability=_to_float(row.get("implied_probability"), 0.5),
                        orderbook=OrderBookSnapshot(
                            best_bid=_to_float(row.get("best_bid"), 0.49),
                            best_ask=_to_float(row.get("best_ask"), 0.51),
                            last_trade_price=_to_float(row.get("last_trade_price"), 0.5),
                            bid_depth=_to_float(row.get("bid_depth"), 1000),
                            ask_depth=_to_float(row.get("ask_depth"), 1000),
                        ),
                        sentiment_score=_to_float(row.get("sentiment_score"), 0.0),
                        news_score=_to_float(row.get("news_score"), 0.0),
                        onchain_flow_score=_to_float(row.get("onchain_flow_score"), 0.0),
                        diagnostics=SourceDiagnostics(
                            gamma_ok=_to_bool(row.get("gamma_ok"), True),
                            clob_ok=_to_bool(row.get("clob_ok"), True),
                            data_api_ok=_to_bool(row.get("data_api_ok"), True),
                            twitter_ok=_to_bool(row.get("twitter_ok"), True),
                            news_ok=_to_bool(row.get("news_ok"), True),
                            onchain_ok=_to_bool(row.get("onchain_ok"), True),
                        ),
                    ),
                    int(_to_float(row.get("outcome"), 0.0)),
                )
            )
    return rows


def _write_temp_csv(rows: list[tuple[DataBundle, int]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "implied_probability",
                "best_bid",
                "best_ask",
                "last_trade_price",
                "bid_depth",
                "ask_depth",
                "sentiment_score",
                "news_score",
                "onchain_flow_score",
                "gamma_ok",
                "clob_ok",
                "data_api_ok",
                "twitter_ok",
                "news_ok",
                "onchain_ok",
                "outcome",
            ]
        )
        for bundle, outcome in rows:
            writer.writerow(
                [
                    bundle.implied_probability,
                    bundle.orderbook.best_bid,
                    bundle.orderbook.best_ask,
                    bundle.orderbook.last_trade_price,
                    bundle.orderbook.bid_depth,
                    bundle.orderbook.ask_depth,
                    bundle.sentiment_score,
                    bundle.news_score,
                    bundle.onchain_flow_score,
                    bundle.diagnostics.gamma_ok,
                    bundle.diagnostics.clob_ok,
                    bundle.diagnostics.data_api_ok,
                    bundle.diagnostics.twitter_ok,
                    bundle.diagnostics.news_ok,
                    bundle.diagnostics.onchain_ok,
                    outcome,
                ]
            )


def run_walk_forward(
    csv_path: str,
    config: AgentConfig | None = None,
    train_size: int = 60,
    test_size: int = 20,
) -> tuple[WalkForwardSummary, list[FoldResult]]:
    cfg = config or AgentConfig()
    data = _read_dataset(csv_path)

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

        tmp_path = f"/tmp/wf_train_{fold_num}.csv"
        _write_temp_csv(train_slice, tmp_path)
        tuned = tune_thresholds(tmp_path, config=cfg)

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
            outcomes.append(1 if outcome > 0 else 0)

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

        fold_result = FoldResult(
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
        folds.append(fold_result)

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
