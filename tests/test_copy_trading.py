from agent.config import APIConfig
from agent.copy_trading import WalletStats, compute_decision_scores, top_wallets_for_copy_trading


def test_compute_decision_scores_orders_descending():
    wallets = [
        WalletStats("a", 100, 70, 0.70, 10000, 1.5, 0.10, 0.8, 0.7, 0.0),
        WalletStats("b", 100, 55, 0.55, 5000, 0.5, 0.30, 0.5, 0.5, 0.0),
        WalletStats("c", 100, 65, 0.65, 8000, 1.2, 0.12, 0.7, 0.6, 0.0),
    ]
    scored = compute_decision_scores(wallets)

    assert scored[0].decision_score >= scored[1].decision_score >= scored[2].decision_score


def test_top_wallets_returns_5():
    wallets = top_wallets_for_copy_trading(APIConfig(), top_n=5)
    assert len(wallets) == 5
    assert all(0.0 <= w.decision_score <= 1.0 for w in wallets)
