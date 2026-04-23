from dataclasses import dataclass
import csv

from .config import AgentConfig
from .data_sources import DataBundle, SourceDiagnostics
from .metrics import brier_score, calibration_curve, log_loss
from .models import OrderBookSnapshot
from .strategy import estimate_fair_probability


@dataclass
class BacktestSummary:
    rows: int
    brier: float
    logloss: float
    avg_confidence: float
    avg_edge_bps: float


def _to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "y", "ok"}


def run_backtest(csv_path: str, config: AgentConfig | None = None) -> tuple[BacktestSummary, list[dict[str, float]]]:
    cfg = config or AgentConfig()

    predictions: list[float] = []
    outcomes: list[int] = []
    confidences: list[float] = []
    edges_bps: list[float] = []

    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            data = DataBundle(
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
            )
            fair_probability, confidence, _ = estimate_fair_probability(data, cfg.strategy)
            outcome = int(_to_float(row.get("outcome"), 0.0))

            predictions.append(fair_probability)
            outcomes.append(1 if outcome > 0 else 0)
            confidences.append(confidence)
            edges_bps.append((fair_probability - data.implied_probability) * 10_000)

    summary = BacktestSummary(
        rows=len(predictions),
        brier=brier_score(predictions, outcomes),
        logloss=log_loss(predictions, outcomes),
        avg_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        avg_edge_bps=sum(edges_bps) / len(edges_bps) if edges_bps else 0.0,
    )

    curve = calibration_curve(predictions, outcomes, bins=10)
    curve_rows = [
        {
            "bin_lower": c.lower,
            "bin_upper": c.upper,
            "avg_predicted": c.avg_predicted,
            "observed_rate": c.observed_rate,
            "count": float(c.count),
        }
        for c in curve
    ]
    return summary, curve_rows
