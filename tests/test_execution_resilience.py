from agent.execution import ExecutionResult, OrderExecutor, OrderRequest, ResilientExecutor


class AlwaysFailExecutor(OrderExecutor):
    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        return ExecutionResult(
            accepted=False,
            order_id=None,
            status="FAILED",
            message="temp fail",
            timestamp_utc="now",
        )


class CountingSuccessExecutor(OrderExecutor):
    def __init__(self):
        self.calls = 0

    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        self.calls += 1
        return ExecutionResult(
            accepted=True,
            order_id=f"ok-{self.calls}",
            status="ACCEPTED",
            message="ok",
            timestamp_utc="now",
        )


def _request() -> OrderRequest:
    return OrderRequest(
        market_id="m1",
        side="BUY",
        price=0.5,
        size_usd=50,
        idempotency_key="abc",
    )


def test_resilient_executor_idempotency_cache():
    inner = CountingSuccessExecutor()
    executor = ResilientExecutor(inner=inner)

    first = executor.submit_order(_request())
    second = executor.submit_order(_request())

    assert first.accepted is True
    assert second.accepted is True
    assert first.order_id == second.order_id
    assert inner.calls == 1


def test_resilient_executor_circuit_breaker_opens():
    inner = AlwaysFailExecutor()
    executor = ResilientExecutor(inner=inner, max_retries=0, failure_threshold=2, circuit_cooldown_sec=60)

    executor.submit_order(_request())
    executor.submit_order(
        OrderRequest(market_id="m2", side="BUY", price=0.5, size_usd=50, idempotency_key="def")
    )
    blocked = executor.submit_order(
        OrderRequest(market_id="m3", side="BUY", price=0.5, size_usd=50, idempotency_key="ghi")
    )

    assert blocked.status == "CIRCUIT_OPEN"
