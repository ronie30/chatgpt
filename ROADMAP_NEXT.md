# Next Steps (Production Hardening)

## 1) Live execution layer (prioritas tertinggi)
- Implement order placement/cancel/update untuk CLOB dengan signer/auth.
- Tambah idempotency key dan retry policy yang aman.
- Tambah circuit breaker ketika spread melebar atau latency API meningkat.

## 2) Streaming data pipeline
- Integrasi WebSocket market channel untuk best bid/ask, last trade, dan event resolve.
- Simpan snapshot orderbook + sinyal ke storage time-series.

## 3) Model calibration & governance
- Jalankan tuning + walk-forward secara terjadwal (harian/mingguan).
- Simpan parameter terbaik per market regime (high vol vs low vol).
- Tambah report reliability (Brier trend, calibration drift, hit-rate).

## 4) Risk control tingkat portofolio
- Position netting lintas market event yang berkorelasi.
- Daily loss limit + auto de-risk mode.
- Exposure cap per kategori event (politik, sports, macro).

## 5) Monitoring & observability
- Dashboard untuk API health, source diagnostics, order fill, slippage, PnL.
- Alerting untuk anomali (disconnect websocket, fill ratio turun, drawdown naik).

## 6) Deployment workflow
- Tambah CI checks: tests + static typing + linting.
- Tambah paper-trading environment dengan replay data historis.
- Setelah stabil, rollout live bertahap dengan ukuran posisi minimum.
