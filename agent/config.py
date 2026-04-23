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
    min_expected_value_bps: float = float(os.getenv("MIN_EXPECTED_VALUE_BPS", "40"))
    min_liquidity_score: float = float(os.getenv("MIN_LIQUIDITY_SCORE", "0.40"))
    min_source_health: float = float(os.getenv("MIN_SOURCE_HEALTH", "0.34"))


@dataclass
class StrategyConfig:
    edge_threshold: float = float(os.getenv("EDGE_THRESHOLD", "0.03"))
    sentiment_weight: float = float(os.getenv("SENTIMENT_WEIGHT", "0.20"))
    onchain_weight: float = float(os.getenv("ONCHAIN_WEIGHT", "0.25"))
    orderflow_weight: float = float(os.getenv("ORDERFLOW_WEIGHT", "0.35"))
    news_weight: float = float(os.getenv("NEWS_WEIGHT", "0.20"))

    prior_strength: float = float(os.getenv("PRIOR_STRENGTH", "0.55"))
    disagreement_penalty_weight: float = float(os.getenv("DISAGREEMENT_PENALTY_WEIGHT", "0.35"))
    entropy_penalty_weight: float = float(os.getenv("ENTROPY_PENALTY_WEIGHT", "0.20"))
    disagreement_penalty_scale: float = float(os.getenv("DISAGREEMENT_PENALTY_SCALE", "0.08"))
    entropy_penalty_scale: float = float(os.getenv("ENTROPY_PENALTY_SCALE", "0.05"))

    confidence_consensus_weight: float = float(os.getenv("CONFIDENCE_CONSENSUS_WEIGHT", "0.45"))
    confidence_orderflow_weight: float = float(os.getenv("CONFIDENCE_ORDERFLOW_WEIGHT", "0.30"))
    confidence_source_health_weight: float = float(os.getenv("CONFIDENCE_SOURCE_HEALTH_WEIGHT", "0.25"))


@dataclass
class QualityConfig:
    window: int = int(os.getenv("QUALITY_WINDOW", "50"))
    min_history: int = int(os.getenv("QUALITY_MIN_HISTORY", "10"))
    implied_z_threshold: float = float(os.getenv("QUALITY_IMPLIED_Z_THRESHOLD", "4.0"))
    spread_z_threshold: float = float(os.getenv("QUALITY_SPREAD_Z_THRESHOLD", "4.0"))
    depth_z_threshold: float = float(os.getenv("QUALITY_DEPTH_Z_THRESHOLD", "4.5"))
    flatline_relative_jump_threshold: float = float(os.getenv("QUALITY_RELATIVE_JUMP_THRESHOLD", "0.25"))
    anomaly_penalty_per_flag: float = float(os.getenv("QUALITY_ANOMALY_PENALTY", "0.25"))


@dataclass
class RegimeConfig:
    spread_norm: float = float(os.getenv("REGIME_SPREAD_NORM", "0.05"))
    spread_weight: float = float(os.getenv("REGIME_SPREAD_WEIGHT", "0.55"))
    dispersion_weight: float = float(os.getenv("REGIME_DISPERSION_WEIGHT", "0.45"))
    high_vol_threshold: float = float(os.getenv("REGIME_HIGH_VOL_THRESHOLD", "0.70"))
    mid_vol_threshold: float = float(os.getenv("REGIME_MID_VOL_THRESHOLD", "0.40"))

    high_vol_risk_multiplier: float = float(os.getenv("REGIME_HIGH_VOL_RISK_MULTIPLIER", "0.45"))
    high_vol_confidence_multiplier: float = float(os.getenv("REGIME_HIGH_VOL_CONFIDENCE_MULTIPLIER", "0.85"))
    mid_vol_risk_multiplier: float = float(os.getenv("REGIME_MID_VOL_RISK_MULTIPLIER", "0.70"))
    mid_vol_confidence_multiplier: float = float(os.getenv("REGIME_MID_VOL_CONFIDENCE_MULTIPLIER", "0.93"))
    low_vol_risk_multiplier: float = float(os.getenv("REGIME_LOW_VOL_RISK_MULTIPLIER", "1.0"))
    low_vol_confidence_multiplier: float = float(os.getenv("REGIME_LOW_VOL_CONFIDENCE_MULTIPLIER", "1.0"))


@dataclass
class TuningConfig:
    win_rate_bonus: float = float(os.getenv("TUNING_WIN_RATE_BONUS", "2000"))
    no_trade_penalty: float = float(os.getenv("TUNING_NO_TRADE_PENALTY", "50"))


@dataclass
class AgentConfig:
    api: APIConfig = field(default_factory=APIConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    tuning: TuningConfig = field(default_factory=TuningConfig)
