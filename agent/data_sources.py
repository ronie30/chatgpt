from dataclasses import dataclass
import hashlib
import json
import random
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import APIConfig
from .math_utils import clip
from .models import OrderBookSnapshot
from .sentiment import lexicon_sentiment


@dataclass
class SourceDiagnostics:
    gamma_ok: bool
    clob_ok: bool
    data_api_ok: bool
    twitter_ok: bool
    news_ok: bool
    onchain_ok: bool


@dataclass
class DataBundle:
    implied_probability: float
    orderbook: OrderBookSnapshot
    sentiment_score: float
    news_score: float
    onchain_flow_score: float
    diagnostics: SourceDiagnostics


class HTTPJSONClient:
    def __init__(self, timeout_sec: float = 8.0):
        self.timeout_sec = timeout_sec

    def get_json(self, url: str, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> Any:
        final_url = f"{url}?{urlencode(params)}" if params else url
        req = Request(final_url, headers=headers or {})
        with urlopen(req, timeout=self.timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))


class PolymarketDataClient:
    """Connector produksi ringan untuk sumber data prioritas.

    Jika endpoint/API key tidak tersedia atau error, agent fallback ke data simulasi
    deterministik supaya pipeline tetap berjalan.
    """

    def __init__(self, api_cfg: APIConfig):
        self.cfg = api_cfg
        self.http = HTTPJSONClient(timeout_sec=api_cfg.request_timeout_sec)

    def fetch_data_bundle(self, market_id: str) -> DataBundle:
        implied_probability, gamma_ok = self._fetch_implied_probability(market_id)
        orderbook, clob_ok = self._fetch_orderbook(market_id)
        sentiment_score, twitter_ok = self._fetch_twitter_sentiment(market_id)
        news_score, news_ok = self._fetch_news_score(market_id)
        onchain_flow_score, data_api_ok, onchain_ok = self._fetch_onchain_flow_score(market_id)

        return DataBundle(
            implied_probability=implied_probability,
            orderbook=orderbook,
            sentiment_score=sentiment_score,
            news_score=news_score,
            onchain_flow_score=onchain_flow_score,
            diagnostics=SourceDiagnostics(
                gamma_ok=gamma_ok,
                clob_ok=clob_ok,
                data_api_ok=data_api_ok,
                twitter_ok=twitter_ok,
                news_ok=news_ok,
                onchain_ok=onchain_ok,
            ),
        )

    def _fetch_implied_probability(self, market_id: str) -> tuple[float, bool]:
        try:
            payload = self.http.get_json(f"{self.cfg.gamma_base_url}/markets/{market_id}")
            value = payload.get("probability") or payload.get("outcomePrices", [None])[0]
            prob = self._safe_probability(value)
            if prob is not None:
                return prob, True
        except Exception:
            pass
        return self._rand(market_id, "implied", 0.2, 0.8), False

    def _fetch_orderbook(self, market_id: str) -> tuple[OrderBookSnapshot, bool]:
        try:
            payload = self.http.get_json(f"{self.cfg.clob_base_url}/book", params={"market": market_id})
            best_bid = float((payload.get("bids") or [[0.0]])[0][0])
            best_ask = float((payload.get("asks") or [[1.0]])[0][0])
            bid_depth = sum(float(level[1]) for level in (payload.get("bids") or [])[:10])
            ask_depth = sum(float(level[1]) for level in (payload.get("asks") or [])[:10])
            last_trade = float(payload.get("last_trade_price") or (best_bid + best_ask) / 2)
            return (
                OrderBookSnapshot(
                    best_bid=clip(best_bid, 0.01, 0.99),
                    best_ask=clip(best_ask, 0.01, 0.99),
                    last_trade_price=clip(last_trade, 0.01, 0.99),
                    bid_depth=max(0.0, bid_depth),
                    ask_depth=max(0.0, ask_depth),
                ),
                True,
            )
        except Exception:
            pass

        last_price = self._rand(market_id, "last", 0.2, 0.8)
        spread = self._rand(market_id, "spread", 0.005, 0.03)
        best_bid = max(0.01, last_price - spread / 2)
        best_ask = min(0.99, last_price + spread / 2)
        return (
            OrderBookSnapshot(
                best_bid=best_bid,
                best_ask=best_ask,
                last_trade_price=last_price,
                bid_depth=self._rand(market_id, "bid_depth", 500, 5000),
                ask_depth=self._rand(market_id, "ask_depth", 500, 5000),
            ),
            False,
        )

    def _fetch_twitter_sentiment(self, market_id: str) -> tuple[float, bool]:
        if not self.cfg.twitter_bearer_token:
            return self._rand(market_id, "twitter", -0.3, 0.3), False

        try:
            headers = {"Authorization": f"Bearer {self.cfg.twitter_bearer_token}"}
            payload = self.http.get_json(
                f"{self.cfg.twitter_base_url}/tweets/search/recent",
                headers=headers,
                params={"query": market_id, "max_results": 25, "tweet.fields": "text"},
            )
            texts = [item.get("text", "") for item in payload.get("data", [])]
            return lexicon_sentiment(texts), True
        except Exception:
            return self._rand(market_id, "twitter", -0.3, 0.3), False

    def _fetch_news_score(self, market_id: str) -> tuple[float, bool]:
        if not self.cfg.news_api_key:
            return self._rand(market_id, "news", -0.3, 0.3), False

        try:
            payload = self.http.get_json(
                f"{self.cfg.news_base_url}/everything",
                params={"q": market_id, "pageSize": 25, "apiKey": self.cfg.news_api_key},
            )
            texts = [
                f"{article.get('title', '')} {article.get('description', '')}" for article in payload.get("articles", [])
            ]
            return lexicon_sentiment(texts), True
        except Exception:
            return self._rand(market_id, "news", -0.3, 0.3), False

    def _fetch_onchain_flow_score(self, market_id: str) -> tuple[float, bool, bool]:
        data_api_ok = False
        onchain_ok = False
        scores: list[float] = []

        try:
            payload = self.http.get_json(f"{self.cfg.data_api_base_url}/markets/{market_id}")
            volume = float(payload.get("volume", 0.0))
            open_interest = float(payload.get("openInterest", 0.0))
            if open_interest > 0:
                scores.append(max(-1.0, min(1.0, (volume / open_interest - 1.0) / 2.0)))
                data_api_ok = True
        except Exception:
            pass

        # lightweight forensic proxy via Polygonscan/Etherscan tx count
        tx_score = self._forensic_tx_score(market_id)
        if tx_score is not None:
            scores.append(tx_score)
            onchain_ok = True

        if scores:
            return sum(scores) / len(scores), data_api_ok, onchain_ok
        return self._rand(market_id, "onchain", -0.3, 0.3), data_api_ok, onchain_ok

    def _forensic_tx_score(self, market_id: str) -> float | None:
        if not self.cfg.polygonscan_api_key:
            return None

        try:
            payload = self.http.get_json(
                self.cfg.polygonscan_base_url,
                params={
                    "module": "logs",
                    "action": "getLogs",
                    "topic0": market_id,
                    "apikey": self.cfg.polygonscan_api_key,
                },
            )
            logs = payload.get("result", [])
            tx_count = len(logs)
            return max(-1.0, min(1.0, (tx_count - 20) / 40))
        except Exception:
            return None

    def _safe_probability(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            parsed = float(value)
            if parsed > 1:
                parsed /= 100
            return clip(parsed, 0.01, 0.99)
        except (TypeError, ValueError):
            return None

    def _rand(self, market_id: str, salt: str, lo: float, hi: float) -> float:
        seed_input = f"{market_id}:{salt}".encode("utf-8")
        seed = int(hashlib.sha256(seed_input).hexdigest()[:8], 16)
        return random.Random(seed).uniform(lo, hi)
