import math


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def clip_probability(value: float, lo: float = 1e-6, hi: float = 1 - 1e-6) -> float:
    return clip(value, lo, hi)


def sigmoid(value: float) -> float:
    if value >= 30:
        return 1.0
    if value <= -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-value))


def logit(probability: float) -> float:
    p = clip_probability(probability)
    return math.log(p / (1.0 - p))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if abs(denominator) <= 1e-12:
        return default
    return numerator / denominator


def depth_imbalance(bid_depth: float, ask_depth: float) -> float:
    total = bid_depth + ask_depth
    return safe_divide(bid_depth - ask_depth, total, default=0.0)
