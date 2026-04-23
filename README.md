# Professional Polymarket Trading Agent

Agent ini adalah fondasi **professional-grade decision engine** untuk market Polymarket dengan pendekatan multi-sumber data, analytics, dan risk management.

## Cakupan Sumber Data (Prioritas)

1. **Polymarket Gamma API** (market metadata/event/search)
2. **Polymarket CLOB API** (orderbook dan harga)
3. **Polymarket Data API** (volume/open interest)
4. **Polymarket WebSocket** (siap ditambahkan untuk streaming live)
5. **On-chain analytics** (Dune/Goldsky/Allium)
6. **Polygonscan/Etherscan** (forensic logs)
7. **Twitter API** (sentimen real-time)
8. **News API / RSS** (sentimen berita)
9. **Google Trends / GDELT** (opsional, bisa ditambah sebagai feature baru)

> Implementasi saat ini sudah berisi REST connector nyata dengan fallback aman (deterministic simulation) agar agent tetap berjalan ketika API unavailable.

## Arsitektur

- `agent/config.py`: konfigurasi endpoint + API key.
- `agent/data_sources.py`: connector HTTP, sentiment scorer, forensic score, diagnostics kesehatan sumber data.
- `agent/strategy.py`: ensemble scoring untuk estimasi fair probability + confidence.
- `agent/risk.py`: position sizing (capped Kelly).
- `agent/orchestrator.py`: keputusan BUY/SELL/HOLD dengan penalti confidence berbasis kesehatan sumber data.
- `agent/main.py`: CLI runner.

## Setup API Key

Salin env berikut ke shell/secret manager:

```bash
export POLYMARKET_API_KEY="..."
export TWITTER_BEARER_TOKEN="..."
export NEWS_API_KEY="..."
export POLYGONSCAN_API_KEY="..."
export ETHERSCAN_API_KEY="..."
export DUNE_API_KEY="..."
export GOLDSKY_API_KEY="..."
export ALLIUM_API_KEY="..."
```

Opsional override endpoint:

```bash
export GAMMA_BASE_URL="https://gamma-api.polymarket.com"
export CLOB_BASE_URL="https://clob.polymarket.com"
export DATA_API_BASE_URL="https://data-api.polymarket.com"
```

## Menjalankan Agent

```bash
python -m agent.main --market-id <POLYMARKET_MARKET_ID> --bankroll 1000
```

Output:
- `signal`: BUY / SELL / HOLD
- `target_price`: fair probability
- `edge`: selisih fair vs implied
- `size_usd`: rekomendasi ukuran posisi
- `confidence`: confidence efektif (setelah penalti source health)
- `rationale`: ringkasan alasan sinyal

## Production Hardening (Next Step)

- Integrasikan websocket listener untuk last trade + best bid/ask streaming.
- Tambahkan order execution signer + auth flow resmi Polymarket CLOB.
- Simpan semua snapshot ke time-series DB untuk backtest dan model retraining.
- Tambah monitoring (latensi API, hit ratio sinyal, drawdown, slippage).
- Jalankan paper trading minimal 2–4 minggu sebelum live.

## Disclaimer

Agent ini alat bantu analitik/trading automation. Tidak menjamin profit dan tetap memerlukan validasi strategi, manajemen risiko, serta kepatuhan regulasi di yurisdiksi Anda.
