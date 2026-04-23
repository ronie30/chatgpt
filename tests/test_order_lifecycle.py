from agent.execution import OrderRequest, PaperExecutor


def test_paper_order_lifecycle_cancel_and_status():
    executor = PaperExecutor(max_notional_usd=100)
    placed = executor.submit_order(OrderRequest("m1", "BUY", 0.5, 10, "id-1"))

    assert placed.accepted is True
    assert placed.order_id is not None

    status_before = executor.get_order_status(placed.order_id)
    assert status_before.status == "ACCEPTED"

    canceled = executor.cancel_order(placed.order_id)
    assert canceled.status == "CANCELED"

    status_after = executor.get_order_status(placed.order_id)
    assert status_after.status == "CANCELED"
