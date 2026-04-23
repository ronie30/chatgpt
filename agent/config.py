from dataclasses import dataclass, field
import os


@dataclass
class APIConfig:
    gamma_base_url: str = os.getenv("GAMMA_BASE_URL", "https://gamma-api.polymarket.com")
    clob_base_url: str = os.getenv("CLOB_BASE_URL", "https://clob.polymarket.com")
    data_api_base_url: str = os.getenv("DATA_API_BASE_URL", "https://data-api.polymarket.com")

    polymarket_api_key: str | None = os.getenv("POLYMARKET_API_KEY")
    twitter_bearer_token: str | None = os.getenv("TWITTER_BEARER_TOKEN")
    news_api_key: str | None = os.getenv("NEWS_API_KEY")
    polygonscan_api_key: str | None = os.getenv("POLYGONSCAN_API_KEY")
    etherscan_api_key: str | None = os.getenv("ETHERSCAN_API_KEY")
    dune_api_key: str | None = os.getenv("DUNE_API_KEY")
    goldsky_api_key: str | None = os.getenv("GOLDSKY_API_KEY")
    allium_api_key: str | None = os.getenv("ALLIUM_API_KEY")

    polygonscan_base_url: str = os.getenv("POLYGONSCAN_BASE_URL", "https://api.polygonscan.com/api")
    etherscan_base_url: str = os.getenv("ETHERSCAN_BASE_URL", "https://api.etherscan.io/api")
    twitter_base_url: str = os.getenv("TWITTER_BASE_URL", "https://api.twitter.com/2")
    news_base_url: str = os.getenv("NEWS_BASE_URL", "https://newsapi.org/v2")
    request_timeout_sec: float = float(os.getenv("REQUEST_TIMEOUT_SEC", "8"))


@dataclass
class RiskConfig:
    max_position_usd: float = float(os.getenv("MAX_POSITION_USD", "250"))
    max_portfolio_exposure: float = float(os.getenv("MAX_PORTFOLIO_EXPOSURE", "0.25"))
    kelly_fraction_cap: float = float(os.getenv("KELLY_FRACTION_CAP", "0.25"))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.60"))
    max_drawdown_stop: float = float(os.getenv("MAX_DRAWDOWN_STOP", "0.10"))


@dataclass
class StrategyConfig:
    edge_threshold: float = float(os.getenv("EDGE_THRESHOLD", "0.03"))
    sentiment_weight: float = float(os.getenv("SENTIMENT_WEIGHT", "0.20"))
    onchain_weight: float = float(os.getenv("ONCHAIN_WEIGHT", "0.25"))
    orderflow_weight: float = float(os.getenv("ORDERFLOW_WEIGHT", "0.35"))
    news_weight: float = float(os.getenv("NEWS_WEIGHT", "0.20"))


@dataclass
class AgentConfig:
    api: APIConfig = field(default_factory=APIConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
