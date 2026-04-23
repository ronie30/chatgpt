import argparse
from dataclasses import asdict

from .backtest import run_backtest
from .config import AgentConfig
from .execution import LiveCLOBExecutor, PaperExecutor, ResilientExecutor
from .order_ledger import CSVOrderLedger
from .orchestrator import TradingAgent
from .tuning import tune_thresholds
from .walk_forward import run_walk_forward


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket multi-source trading agent")
    parser.add_argument("--market-id", help="Polymarket market id")
    parser.add_argument("--bankroll", type=float, default=1000.0, help="Bankroll in USD")
    parser.add_argument("--backtest-file", help="CSV path for offline backtest/calibration")
    parser.add_argument("--tune-file", help="CSV path for threshold tuning")
    parser.add_argument("--walk-forward-file", help="CSV path for walk-forward validation")
    parser.add_argument("--wf-train-size", type=int, default=60, help="Walk-forward train window size")
    parser.add_argument("--wf-test-size", type=int, default=20, help="Walk-forward test window size")
    parser.add_argument("--execute", action="store_true", help="Execute decision via selected executor")
    parser.add_argument("--executor", choices=["paper", "live"], default="paper", help="Executor backend")
    parser.add_argument("--ledger-path", default="artifacts/order_ledger.csv", help="Order ledger CSV path")
    args = parser.parse_args()

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

    if not args.market_id:
        raise SystemExit(
            "--market-id wajib diisi saat tidak menjalankan --backtest-file/--tune-file/--walk-forward-file"
        )

    cfg = AgentConfig()
    ledger = CSVOrderLedger(path=args.ledger_path)
    if args.executor == "live":
        live = LiveCLOBExecutor(api_cfg=cfg.api, ledger=ledger)
        selected_executor = ResilientExecutor(inner=live, max_retries=1, retry_backoff_sec=0.2)
    else:
        paper = PaperExecutor(max_notional_usd=cfg.risk.max_position_usd, ledger=ledger)
        selected_executor = ResilientExecutor(inner=paper, max_retries=2, retry_backoff_sec=0.05)

    agent = TradingAgent(config=cfg, bankroll_usd=args.bankroll, executor=selected_executor)

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
