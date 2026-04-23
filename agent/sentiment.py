from .math_utils import clip, safe_divide


POSITIVE_WORDS = {
    "win",
    "wins",
    "bullish",
    "approved",
    "growth",
    "up",
    "positive",
    "beat",
    "strong",
    "surge",
}
NEGATIVE_WORDS = {
    "lose",
    "loses",
    "bearish",
    "rejected",
    "decline",
    "down",
    "negative",
    "miss",
    "weak",
    "drop",
}


def lexicon_sentiment(texts: list[str]) -> float:
    if not texts:
        return 0.0

    score = 0
    words_seen = 0
    for text in texts:
        for token in text.lower().split():
            cleaned = token.strip(".,:;!?()[]{}\"'`")
            if not cleaned:
                continue
            words_seen += 1
            if cleaned in POSITIVE_WORDS:
                score += 1
            elif cleaned in NEGATIVE_WORDS:
                score -= 1

    normalized = safe_divide(score, max(1, words_seen // 4), default=0.0)
    return clip(normalized, -1.0, 1.0)
