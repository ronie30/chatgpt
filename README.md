# Professional Polymarket Trading Agent (High-Trust Architecture)

Agent ini dirancang untuk menghasilkan keputusan trading yang **lebih akurat, robust, dan dapat diaudit** melalui:

- Multi-source data fusion (Gamma, CLOB, Data API, Twitter, News, forensic chain logs).
- Probabilistic inference dengan prior market + signal posterior.
- Quality gates (source health, liquidity, expected value, confidence).
- Risk sizing berbasis Kelly cap + batas exposure.

## Komponen Utama

- `agent/data_sources.py`: connector REST nyata + deterministic fallback + diagnostics.
- `agent/strategy.py`: posterior fair probability dengan disagreement/entropy penalty.
- `agent/feature_engineering.py`: liquidity, entropy, dan feature normalization.
- `agent/orchestrator.py`: decision engine BUY/SELL/HOLD dengan quality gate berlapis.
- `agent/risk.py`: sizing yang konservatif dan bounded.

## Data Sources Prioritas

1. Polymarket Gamma API
2. Polymarket CLOB API / WebSocket
3. Polymarket Data API
4. On-chain analytics (Dune/Goldsky/Allium)
5. Polygonscan / Etherscan
6. Twitter API
7. News API / RSS
8. Google Trends / GDELT (opsional)

## Setup

Gunakan `.env.example` lalu isi semua API key yang tersedia.

```bash
python -m agent.main --market-id <POLYMARKET_MARKET_ID> --bankroll 1000
```

Output berisi:
- `signal`, `target_price`, `edge`, `size_usd`
- `confidence`, `expected_value_bps`, `source_health`
- `rationale` untuk audit keputusan

## Catatan Profesional

- "Akurasi sangat tinggi" dicapai lewat kombinasi data quality + kalibrasi model + evaluasi berulang, bukan dari satu formula.
- Lakukan paper trading dan calibration period sebelum live deployment.
- Sistem ini adalah decision engine; tetap butuh governance, monitoring, dan risk review manusia.


## Backtest & Calibration

Anda bisa evaluasi kualitas prediksi historis dengan CSV offline:

```bash
python -m agent.main --backtest-file tests/data/backtest_sample.csv
```

Kolom minimal CSV: `implied_probability`, orderbook fields, score fields, diagnostics flags, dan `outcome` (0/1).
Output mencakup `brier`, `logloss`, rata-rata confidence/edge, serta calibration curve 10-bin.
