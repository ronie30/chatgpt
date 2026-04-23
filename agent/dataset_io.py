import csv

from .data_sources import DataBundle, SourceDiagnostics
from .models import OrderBookSnapshot


def to_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "ok"}


def load_labeled_bundles(csv_path: str) -> list[tuple[DataBundle, int]]:
    rows: list[tuple[DataBundle, int]] = []
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            bundle = DataBundle(
                implied_probability=to_float(row.get("implied_probability"), 0.5),
                orderbook=OrderBookSnapshot(
                    best_bid=to_float(row.get("best_bid"), 0.49),
                    best_ask=to_float(row.get("best_ask"), 0.51),
                    last_trade_price=to_float(row.get("last_trade_price"), 0.5),
                    bid_depth=to_float(row.get("bid_depth"), 1000),
                    ask_depth=to_float(row.get("ask_depth"), 1000),
                ),
                sentiment_score=to_float(row.get("sentiment_score"), 0.0),
                news_score=to_float(row.get("news_score"), 0.0),
                onchain_flow_score=to_float(row.get("onchain_flow_score"), 0.0),
                diagnostics=SourceDiagnostics(
                    gamma_ok=to_bool(row.get("gamma_ok"), True),
                    clob_ok=to_bool(row.get("clob_ok"), True),
                    data_api_ok=to_bool(row.get("data_api_ok"), True),
                    twitter_ok=to_bool(row.get("twitter_ok"), True),
                    news_ok=to_bool(row.get("news_ok"), True),
                    onchain_ok=to_bool(row.get("onchain_ok"), True),
                ),
            )
            outcome = 1 if to_float(row.get("outcome"), 0.0) > 0 else 0
            rows.append((bundle, outcome))
    return rows
