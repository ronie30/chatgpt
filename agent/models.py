from dataclasses import dataclass
from typing import Literal


Signal = Literal["BUY", "SELL", "HOLD"]


@dataclass
class OrderBookSnapshot:
    best_bid: float
    best_ask: float
    last_trade_price: float
    bid_depth: float
    ask_depth: float


@dataclass
class MarketFeatures:
    market_id: str
    implied_probability: float
    fair_probability: float
    sentiment_score: float
    news_score: float
    onchain_flow_score: float
    orderflow_imbalance: float
    liquidity_score: float
    confidence: float


@dataclass
class TradeDecision:
    market_id: str
    signal: Signal
    target_price: float
    edge: float
    size_usd: float
    confidence: float
    rationale: str
