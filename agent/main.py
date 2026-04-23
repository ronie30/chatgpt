import argparse
from dataclasses import asdict

from .orchestrator import TradingAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket multi-source trading agent")
    parser.add_argument("--market-id", required=True, help="Polymarket market id")
    parser.add_argument("--bankroll", type=float, default=1000.0, help="Bankroll in USD")
    args = parser.parse_args()

    agent = TradingAgent(bankroll_usd=args.bankroll)
    decision = agent.evaluate_market(args.market_id)

    print("=== Trade Decision ===")
    for k, v in asdict(decision).items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
