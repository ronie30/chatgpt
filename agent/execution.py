from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import time
from typing import Literal
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import APIConfig
from .models import TradeDecision
from .order_ledger import CSVOrderLedger, LedgerEntry, now_utc


OrderStatus = Literal[
    "NEW",
    "ACCEPTED",
    "PARTIAL_FILL",
    "FILLED",
    "CANCELED",
    "REJECTED",
    "FAILED",
    "LIVE_DISABLED",
    "HTTP_ERROR",
    "NETWORK_ERROR",
    "TIMEOUT",
    "UNKNOWN",
    "CIRCUIT_OPEN",
]


@dataclass
class OrderRequest:
    market_id: str
    side: str
    price: float
    size_usd: float
    idempotency_key: str


@dataclass
class ExecutionResult:
    accepted: bool
    order_id: str | None
    status: OrderStatus
    message: str
    timestamp_utc: str


class OrderExecutor:
    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> ExecutionResult:
        return ExecutionResult(False, order_id, "UNKNOWN", "cancel_order belum diimplementasi", now_utc())

    def get_order_status(self, order_id: str) -> ExecutionResult:
        return ExecutionResult(False, order_id, "UNKNOWN", "get_order_status belum diimplementasi", now_utc())


class PaperExecutor(OrderExecutor):
    """Dry-run executor dengan order lifecycle state machine sederhana."""

    def __init__(self, max_notional_usd: float = 1000.0, ledger: CSVOrderLedger | None = None):
        self.max_notional_usd = max_notional_usd
        self.ledger = ledger
        self.orders: dict[str, ExecutionResult] = {}

    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        now = datetime.now(timezone.utc).isoformat()

        if request.size_usd <= 0:
            result = ExecutionResult(False, None, "REJECTED", "size_usd harus > 0", now)
            self._log(request, result)
            return result

        if request.size_usd > self.max_notional_usd:
            result = ExecutionResult(False, None, "REJECTED", "Melebihi max_notional_usd executor", now)
            self._log(request, result)
            return result

        order_id = f"paper-{uuid.uuid4()}"
        result = ExecutionResult(
            accepted=True,
            order_id=order_id,
            status="ACCEPTED",
            message=(
                f"Paper order accepted: side={request.side}, market={request.market_id}, "
                f"price={request.price:.4f}, size={request.size_usd:.2f}"
            ),
            timestamp_utc=now,
        )
        self.orders[order_id] = result
        self._log(request, result)
        return result

    def cancel_order(self, order_id: str) -> ExecutionResult:
        now = now_utc()
        existing = self.orders.get(order_id)
        if not existing:
            return ExecutionResult(False, order_id, "UNKNOWN", "Order id tidak ditemukan", now)

        canceled = ExecutionResult(True, order_id, "CANCELED", "Paper order canceled", now)
        self.orders[order_id] = canceled
        return canceled

    def get_order_status(self, order_id: str) -> ExecutionResult:
        return self.orders.get(order_id) or ExecutionResult(False, order_id, "UNKNOWN", "Order id tidak ditemukan", now_utc())

    def _log(self, request: OrderRequest, result: ExecutionResult) -> None:
        if not self.ledger:
            return
        self.ledger.append(
            LedgerEntry(
                timestamp_utc=result.timestamp_utc,
                market_id=request.market_id,
                side=request.side,
                price=request.price,
                size_usd=request.size_usd,
                status=result.status,
                order_id=result.order_id,
                message=result.message,
            )
        )


class LiveCLOBExecutor(OrderExecutor):
    """Live executor skeleton dengan granular error dan endpoint lifecycle dasar."""

    def __init__(self, api_cfg: APIConfig, ledger: CSVOrderLedger | None = None):
        self.api_cfg = api_cfg
        self.ledger = ledger

    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        now = now_utc()
        if not self.api_cfg.polymarket_api_key:
            result = ExecutionResult(False, None, "LIVE_DISABLED", "POLYMARKET_API_KEY belum di-set.", now)
            self._log(request, result)
            return result

        payload = {
            "market": request.market_id,
            "side": request.side,
            "price": request.price,
            "size_usd": request.size_usd,
            "idempotency_key": request.idempotency_key,
        }
        result = self._post_json(path="/orders", payload=payload)
        self._log(request, result)
        return result

    def cancel_order(self, order_id: str) -> ExecutionResult:
        if not self.api_cfg.polymarket_api_key:
            return ExecutionResult(False, order_id, "LIVE_DISABLED", "POLYMARKET_API_KEY belum di-set.", now_utc())

        return self._post_json(path=f"/orders/{order_id}/cancel", payload={"order_id": order_id}, forced_order_id=order_id)

    def get_order_status(self, order_id: str) -> ExecutionResult:
        if not self.api_cfg.polymarket_api_key:
            return ExecutionResult(False, order_id, "LIVE_DISABLED", "POLYMARKET_API_KEY belum di-set.", now_utc())

        now = now_utc()
        try:
            req = self._build_request(path=f"/orders/{order_id}", method="GET")
            with urlopen(req, timeout=self.api_cfg.request_timeout_sec) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
            status = self._normalize_status(str(parsed.get("status", "UNKNOWN")))
            return ExecutionResult(status in {"ACCEPTED", "PARTIAL_FILL", "FILLED"}, order_id, status, "Order status fetched", now)
        except HTTPError as exc:
            return ExecutionResult(False, order_id, "HTTP_ERROR", f"HTTP {exc.code}: {exc.reason}", now)
        except URLError as exc:
            return ExecutionResult(False, order_id, "NETWORK_ERROR", f"Network error: {exc.reason}", now)
        except TimeoutError as exc:
            return ExecutionResult(False, order_id, "TIMEOUT", f"Timeout: {exc}", now)
        except Exception as exc:
            return ExecutionResult(False, order_id, "FAILED", f"Live status failed: {exc}", now)

    def _post_json(self, path: str, payload: dict, forced_order_id: str | None = None) -> ExecutionResult:
        now = now_utc()
        try:
            body = json.dumps(payload).encode("utf-8")
            req = self._build_request(path=path, data=body, method="POST")
            with urlopen(req, timeout=self.api_cfg.request_timeout_sec) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))

            order_id = forced_order_id or str(parsed.get("order_id") or parsed.get("id") or f"live-{uuid.uuid4()}")
            status = self._normalize_status(str(parsed.get("status", "ACCEPTED")))
            return ExecutionResult(status in {"ACCEPTED", "PARTIAL_FILL", "FILLED"}, order_id, status, "Live request submitted", now)
        except HTTPError as exc:
            return ExecutionResult(False, forced_order_id, "HTTP_ERROR", f"HTTP {exc.code}: {exc.reason}", now)
        except URLError as exc:
            return ExecutionResult(False, forced_order_id, "NETWORK_ERROR", f"Network error: {exc.reason}", now)
        except TimeoutError as exc:
            return ExecutionResult(False, forced_order_id, "TIMEOUT", f"Timeout: {exc}", now)
        except Exception as exc:
            return ExecutionResult(False, forced_order_id, "FAILED", f"Live submit failed: {exc}", now)

    def _build_request(self, path: str, data: bytes | None = None, method: str = "POST") -> Request:
        payload = data or b""
        signature = self._sign(payload)
        return Request(
            f"{self.api_cfg.clob_base_url}{path}",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_cfg.polymarket_api_key}",
                "X-Signature": signature,
            },
            method=method,
        )

    def _sign(self, payload: bytes) -> str:
        secret = (self.api_cfg.polymarket_api_key or "").encode("utf-8")
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

    def _normalize_status(self, status: str) -> OrderStatus:
        normalized = status.upper()
        mapping = {
            "OPEN": "ACCEPTED",
            "NEW": "NEW",
            "ACCEPTED": "ACCEPTED",
            "PARTIAL_FILL": "PARTIAL_FILL",
            "FILLED": "FILLED",
            "CANCELED": "CANCELED",
            "REJECTED": "REJECTED",
            "FAILED": "FAILED",
        }
        return mapping.get(normalized, "UNKNOWN")

    def _log(self, request: OrderRequest, result: ExecutionResult) -> None:
        if not self.ledger:
            return
        self.ledger.append(
            LedgerEntry(
                timestamp_utc=result.timestamp_utc,
                market_id=request.market_id,
                side=request.side,
                price=request.price,
                size_usd=request.size_usd,
                status=result.status,
                order_id=result.order_id,
                message=result.message,
            )
        )


class ResilientExecutor(OrderExecutor):
    """Executor wrapper dengan retry, idempotency cache, dan circuit breaker sederhana."""

    def __init__(
        self,
        inner: OrderExecutor,
        max_retries: int = 2,
        retry_backoff_sec: float = 0.05,
        failure_threshold: int = 3,
        circuit_cooldown_sec: float = 5.0,
    ):
        self.inner = inner
        self.max_retries = max_retries
        self.retry_backoff_sec = retry_backoff_sec
        self.failure_threshold = failure_threshold
        self.circuit_cooldown_sec = circuit_cooldown_sec

        self._idempotency_cache: dict[str, ExecutionResult] = {}
        self._consecutive_failures = 0
        self._circuit_opened_at: float | None = None

    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        now_ts = time.time()

        cached = self._idempotency_cache.get(request.idempotency_key)
        if cached is not None:
            return cached

        if self._is_circuit_open(now_ts):
            return ExecutionResult(
                accepted=False,
                order_id=None,
                status="CIRCUIT_OPEN",
                message="Circuit breaker aktif; eksekusi ditunda.",
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            )

        last_result: ExecutionResult | None = None
        for attempt in range(self.max_retries + 1):
            result = self.inner.submit_order(request)
            last_result = result

            if result.accepted:
                self._consecutive_failures = 0
                self._idempotency_cache[request.idempotency_key] = result
                return result

            if result.status in {"REJECTED", "LIVE_DISABLED", "HTTP_ERROR"}:
                self._register_failure(now_ts)
                return result

            if attempt < self.max_retries:
                time.sleep(self.retry_backoff_sec * (attempt + 1))

        self._register_failure(now_ts)
        return last_result or ExecutionResult(
            accepted=False,
            order_id=None,
            status="FAILED",
            message="Unknown executor failure",
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

    def cancel_order(self, order_id: str) -> ExecutionResult:
        return self.inner.cancel_order(order_id)

    def get_order_status(self, order_id: str) -> ExecutionResult:
        return self.inner.get_order_status(order_id)

    def _is_circuit_open(self, now_ts: float) -> bool:
        if self._circuit_opened_at is None:
            return False
        if (now_ts - self._circuit_opened_at) > self.circuit_cooldown_sec:
            self._circuit_opened_at = None
            self._consecutive_failures = 0
            return False
        return True

    def _register_failure(self, now_ts: float) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._circuit_opened_at = now_ts


def decision_to_order_request(decision: TradeDecision) -> OrderRequest | None:
    if decision.signal == "HOLD" or decision.size_usd <= 0:
        return None

    side = "BUY" if decision.signal == "BUY" else "SELL"
    return OrderRequest(
        market_id=decision.market_id,
        side=side,
        price=decision.target_price,
        size_usd=decision.size_usd,
        idempotency_key=f"{decision.market_id}:{side}:{decision.target_price:.4f}:{decision.size_usd:.2f}",
    )
