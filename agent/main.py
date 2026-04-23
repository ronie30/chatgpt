import argparse
from dataclasses import asdict

from .backtest import run_backtest
from .config import AgentConfig
from .execution import LiveCLOBExecutor, PaperExecutor, ResilientExecutor
from .observability import ObservabilityStack
from .order_ledger import CSVOrderLedger
from .orchestrator import TradingAgent
from .tuning import tune_thresholds
from .copy_trading import top_wallets_for_copy_trading
from .reliability import run_reliability_report
from .walk_forward import run_walk_forward


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket multi-source trading agent")
    parser.add_argument("--market-id", help="Polymarket market id")
    parser.add_argument("--bankroll", type=float, default=1000.0, help="Bankroll in USD")
    parser.add_argument("--backtest-file", help="CSV path for offline backtest/calibration")
    parser.add_argument("--tune-file", help="CSV path for threshold tuning")
    parser.add_argument("--walk-forward-file", help="CSV path for walk-forward validation")
    parser.add_argument("--reliability-file", help="CSV path for reliability/drift report")
    parser.add_argument("--wf-train-size", type=int, default=60, help="Walk-forward train window size")
    parser.add_argument("--wf-test-size", type=int, default=20, help="Walk-forward test window size")
    parser.add_argument("--reliability-window", type=int, default=20, help="Window size for drift comparison in reliability report")
    parser.add_argument("--execute", action="store_true", help="Execute decision via selected executor")
    parser.add_argument("--executor", choices=["paper", "live"], default="paper", help="Executor backend")
    parser.add_argument("--ledger-path", default="artifacts/order_ledger.csv", help="Order ledger CSV path")
    parser.add_argument("--cancel-order-id", help="Cancel existing order id")
    parser.add_argument("--status-order-id", help="Get status for existing order id")
    parser.add_argument("--metrics-snapshot", action="store_true", help="Print metrics/alerts snapshot")
    parser.add_argument("--top-wallets", action="store_true", help="Show top 5 wallets for copy trading")
    args = parser.parse_args()

    cfg = AgentConfig()

    if args.top_wallets:
        wallets = top_wallets_for_copy_trading(cfg.api, top_n=5)
        print("=== Top 5 Copy Trading Wallets ===")
        for i, w in enumerate(wallets, start=1):
            print(f"{i}. {w.wallet} | win_rate={w.win_rate:.2%} | pnl=${w.realized_pnl_usd:,.0f} | score={w.decision_score:.3f}")
        return

    if args.backtest_file:
        summary, curve_rows = run_backtest(args.backtest_file)
        print("=== Backtest Summary ===")
        for k, v in asdict(summary).items():
            print(f"{k}: {v}")
        print("=== Calibration Curve (10 bins) ===")
        for row in curve_rows:
            print(row)
        return

    if args.tune_file:
        result = tune_thresholds(args.tune_file)
        print("=== Threshold Tuning Result ===")
        for k, v in asdict(result).items():
            print(f"{k}: {v}")
        return

    if args.reliability_file:
        report = run_reliability_report(
            args.reliability_file,
            config=cfg,
            window_size=args.reliability_window,
        )
        print("=== Reliability Report ===")
        for k, v in asdict(report).items():
            print(f"{k}: {v}")
        return

    if args.walk_forward_file:
        summary, folds = run_walk_forward(
            args.walk_forward_file,
            train_size=args.wf_train_size,
            test_size=args.wf_test_size,
        )
        print("=== Walk-Forward Summary ===")
        for k, v in asdict(summary).items():
            print(f"{k}: {v}")
        print("=== Fold Details ===")
        for fold in folds:
            print(asdict(fold))
        return

    obs = ObservabilityStack()
    ledger = CSVOrderLedger(path=args.ledger_path)
    if args.executor == "live":
        live = LiveCLOBExecutor(api_cfg=cfg.api, ledger=ledger, observer=obs)
        selected_executor = ResilientExecutor(inner=live, max_retries=1, retry_backoff_sec=0.2)
    else:
        paper = PaperExecutor(max_notional_usd=cfg.risk.max_position_usd, ledger=ledger, observer=obs)
        selected_executor = ResilientExecutor(inner=paper, max_retries=2, retry_backoff_sec=0.05)

    agent = TradingAgent(config=cfg, bankroll_usd=args.bankroll, executor=selected_executor, observer=obs)

    if args.metrics_snapshot:
        print("=== Metrics Snapshot ===")
        print(obs.metrics.snapshot())
        print("=== Alerts ===")
        print(obs.alert_messages())
        return

    if args.cancel_order_id:
        result = selected_executor.cancel_order(args.cancel_order_id)
        print("=== Cancel Result ===")
        print(asdict(result))
        return

    if args.status_order_id:
        result = selected_executor.get_order_status(args.status_order_id)
        print("=== Order Status ===")
        print(asdict(result))
        return

    if not args.market_id and not args.cancel_order_id and not args.status_order_id:
        raise SystemExit(
            "--market-id wajib diisi untuk evaluate/execute (tidak wajib untuk status/cancel order)."
        )

    if args.execute:
        result = agent.execute_market(args.market_id)
        print("=== Trade Decision ===")
        for k, v in asdict(result.decision).items():
            print(f"{k}: {v}")
        print("=== Execution ===")
        print(asdict(result.execution) if result.execution else "No order submitted (HOLD)")
        return

    decision = agent.evaluate_market(args.market_id)
    print("=== Trade Decision ===")
    for k, v in asdict(decision).items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
