# Next Sprint Plan (Agar Lebih Matang dan Siap Produksi)

## Sprint 1 — Real CLOB Execution Integration
1. Implement `LiveCLOBExecutor` (auth/signing + place/cancel/update order).
2. Tambah order state machine (`NEW`, `PARTIAL_FILL`, `FILLED`, `CANCELED`, `REJECTED`).
3. Persist order ledger dan execution log ke storage (CSV/SQLite/Postgres).

## Sprint 2 — Realtime Streaming + Feature Store
1. Integrasi WebSocket Polymarket market channel (best bid/ask, last trade, market events).
2. Bangun rolling feature store per market (1m/5m/15m windows).
3. Sinkronisasi fallback REST jika websocket disconnect.

## Sprint 3 — Portfolio-Level Risk Engine
1. Exposure limit lintas market/event category.
2. Daily loss limit + kill switch otomatis.
3. Correlation-aware position netting antar market yang sejenis.

## Sprint 4 — Model Governance & Monitoring
1. Scheduler untuk backtest + tuning + walk-forward berkala.
2. Drift monitor: Brier trend, calibration drift, fill-quality drift.
3. Alerting: circuit breaker frequency, source health drop, data quality anomaly spikes.

## Definition of Done (DoD)
- Semua test unit/integration lulus.
- Paper trading stabil minimal 14 hari.
- Tidak ada critical alert berulang > 3 hari berturut-turut.
- Risk guardrails aktif dan tervalidasi via chaos tests.
