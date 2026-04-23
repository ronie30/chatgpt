from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import time
import uuid
from urllib.request import Request, urlopen

from .config import APIConfig
from .models import TradeDecision
from .order_ledger import CSVOrderLedger, LedgerEntry, now_utc


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
    status: str
    message: str
    timestamp_utc: str


class OrderExecutor:
    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        raise NotImplementedError


class PaperExecutor(OrderExecutor):
    """Dry-run executor: tidak kirim order ke exchange, hanya simulasi accepted/rejected."""

    def __init__(self, max_notional_usd: float = 1000.0, ledger: CSVOrderLedger | None = None):
        self.max_notional_usd = max_notional_usd
        self.ledger = ledger

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

        result = ExecutionResult(
            accepted=True,
            order_id=f"paper-{uuid.uuid4()}",
            status="ACCEPTED",
            message=(
                f"Paper order accepted: side={request.side}, market={request.market_id}, "
                f"price={request.price:.4f}, size={request.size_usd:.2f}"
            ),
            timestamp_utc=now,
        )
        self._log(request, result)
        return result

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
    """Skeleton live executor untuk Polymarket CLOB.

    - Jika API key tidak tersedia, fallback ke response 'LIVE_DISABLED'.
    - Signing memakai HMAC sederhana sebagai placeholder integrasi auth.
    """

    def __init__(self, api_cfg: APIConfig, ledger: CSVOrderLedger | None = None):
        self.api_cfg = api_cfg
        self.ledger = ledger

    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        now = now_utc()
        if not self.api_cfg.polymarket_api_key:
            result = ExecutionResult(False, None, "LIVE_DISABLED", "POLYMARKET_API_KEY belum di-set.", now)
            self._log(request, result)
            return result

        try:
            payload = {
                "market": request.market_id,
                "side": request.side,
                "price": request.price,
                "size_usd": request.size_usd,
                "idempotency_key": request.idempotency_key,
            }
            body = json.dumps(payload).encode("utf-8")
            signature = self._sign(body)
            req = Request(
                f"{self.api_cfg.clob_base_url}/orders",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_cfg.polymarket_api_key}",
                    "X-Signature": signature,
                },
                method="POST",
            )
            with urlopen(req, timeout=self.api_cfg.request_timeout_sec) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))

            result = ExecutionResult(
                accepted=True,
                order_id=str(parsed.get("order_id") or parsed.get("id") or f"live-{uuid.uuid4()}"),
                status="ACCEPTED",
                message="Live order submitted",
                timestamp_utc=now,
            )
            self._log(request, result)
            return result
        except Exception as exc:
            result = ExecutionResult(False, None, "FAILED", f"Live submit failed: {exc}", now)
            self._log(request, result)
            return result

    def _sign(self, payload: bytes) -> str:
        secret = (self.api_cfg.polymarket_api_key or "").encode("utf-8")
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

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

            if result.status == "REJECTED":
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
