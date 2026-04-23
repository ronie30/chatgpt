import argparse
from dataclasses import asdict

from .backtest import run_backtest
from .orchestrator import TradingAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket multi-source trading agent")
    parser.add_argument("--market-id", help="Polymarket market id")
    parser.add_argument("--bankroll", type=float, default=1000.0, help="Bankroll in USD")
    parser.add_argument("--backtest-file", help="CSV path for offline backtest/calibration")
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

    if not args.market_id:
        raise SystemExit("--market-id wajib diisi saat tidak menjalankan --backtest-file")

    agent = TradingAgent(bankroll_usd=args.bankroll)
    decision = agent.evaluate_market(args.market_id)

    print("=== Trade Decision ===")
    for k, v in asdict(decision).items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
