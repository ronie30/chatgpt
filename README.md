# Professional Polymarket Trading Agent (High-Trust Architecture)

Agent ini dirancang untuk menghasilkan keputusan trading yang **lebih akurat, robust, dan dapat diaudit** melalui:

- Multi-source data fusion (Gamma, CLOB, Data API, Twitter, News, forensic chain logs).
- Probabilistic inference dengan prior market + signal posterior.
- Quality gates (source health, liquidity, expected value, confidence).
- Regime-adaptive risk control (LOW_VOL / MID_VOL / HIGH_VOL).
- Data-quality anomaly guard (rolling z-score on implied/spread/depth).
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


## Threshold Tuning (Auto-Optimization)

Untuk meningkatkan akurasi operasional, gunakan grid-search threshold dari data historis:

```bash
python -m agent.main --tune-file tests/data/backtest_sample.csv
```

Output memberikan kombinasi threshold terbaik (`min_confidence`, `edge_threshold`, `min_ev_bps`) berdasarkan utility score, jumlah trade, dan win-rate.


## Walk-Forward Validation (Anti-Overfit)

Untuk validasi yang lebih realistis (train di masa lalu, test di masa depan):

```bash
python -m agent.main --walk-forward-file tests/data/backtest_sample.csv --wf-train-size 3 --wf-test-size 1
```

Mode ini melakukan tuning pada setiap window train, lalu mengevaluasi performa pada window test berikutnya.
Output: ringkasan lintas fold + detail tiap fold (`win_rate`, `avg_ev_bps`, `brier`).


## Paper Execution (Dry-Run)

Untuk melanjutkan eksekusi tanpa risiko order live, gunakan paper executor:

```bash
python -m agent.main --market-id <POLYMARKET_MARKET_ID> --execute
```

Jika sinyal `HOLD`, order tidak dikirim. Jika `BUY/SELL`, sistem membuat paper order dengan idempotency key dan hasil eksekusi terstruktur.
Paper execution sekarang dilengkapi retry, idempotency cache, dan circuit breaker untuk meniru guardrail eksekusi produksi.



## Regime-Adaptive Method (Metode Tambahan)

Agent sekarang mendeteksi regime volatilitas market dan menyesuaikan confidence serta ukuran posisi secara dinamis.
Tujuannya agar performa trading otomatis lebih stabil saat market memasuki kondisi HIGH_VOL.


## Data Quality Guard (Metode Tambahan)

Agent menyimpan rolling history per market dan menahan eksekusi otomatis saat terdeteksi anomali besar pada implied probability, spread, atau depth.
Ini membantu menghindari false signal akibat data glitch/spike sesaat.


## Live Executor Skeleton + Ledger

Gunakan mode executor:

```bash
python -m agent.main --market-id <POLYMARKET_MARKET_ID> --execute --executor paper
python -m agent.main --market-id <POLYMARKET_MARKET_ID> --execute --executor live
```

Semua eksekusi dicatat ke order ledger CSV (`--ledger-path`, default `artifacts/order_ledger.csv`).
Jika `POLYMARKET_API_KEY` belum di-set, live executor akan mengembalikan status `LIVE_DISABLED` (safe-fail).


Lifecycle command contoh:

```bash
python -m agent.main --market-id <POLYMARKET_MARKET_ID> --execute --executor paper
python -m agent.main --status-order-id <ORDER_ID> --executor paper
python -m agent.main --cancel-order-id <ORDER_ID> --executor paper
```


## Observability Production Stack

CLI mendukung snapshot metrik + alert sederhana:

```bash
python -m agent.main --market-id <POLYMARKET_MARKET_ID> --metrics-snapshot
```

Data observability mencakup structured events (`artifacts/agent_events.jsonl`), counter/histogram metrics, dan alert rules berbasis threshold.

## Integration Test Endpoint Nyata (Opt-in)

```bash
RUN_LIVE_INTEGRATION=1 LIVE_TEST_MARKET=<MARKET_ID> pytest -q tests/integration/test_live_endpoint_integration.py
```

Test ini sengaja opt-in agar aman dijalankan di CI tanpa credential.


## Top 5 Wallet Copy Trading (Metode Tambahan)

Untuk melihat 5 wallet dengan winrate/performa terbaik (risk-adjusted scoring):

```bash
python -m agent.main --top-wallets
```

Skor keputusan wallet dihitung secara kompleks dari kombinasi: realized PnL, Sharpe, max drawdown, win-rate, recency, consistency, dan penalti overfit (trade depth rendah).
