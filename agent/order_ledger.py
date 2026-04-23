from dataclasses import dataclass
from datetime import datetime, timezone
import csv
from pathlib import Path


@dataclass
class LedgerEntry:
    timestamp_utc: str
    market_id: str
    side: str
    price: float
    size_usd: float
    status: str
    order_id: str | None
    message: str


class CSVOrderLedger:
    def __init__(self, path: str = "artifacts/order_ledger.csv"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()

    def append(self, entry: LedgerEntry) -> None:
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    entry.timestamp_utc,
                    entry.market_id,
                    entry.side,
                    f"{entry.price:.6f}",
                    f"{entry.size_usd:.2f}",
                    entry.status,
                    entry.order_id or "",
                    entry.message,
                ]
            )

    def _ensure_header(self) -> None:
        if self.path.exists() and self.path.stat().st_size > 0:
            return
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp_utc", "market_id", "side", "price", "size_usd", "status", "order_id", "message"])


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
