# Execution Plan 7 Hari (Production Hardening)

Dokumen ini memecah roadmap menjadi rencana implementasi mingguan yang bisa dieksekusi.

## Tujuan Minggu Ini
- Menyiapkan pondasi **live readiness** tanpa mengorbankan safety.
- Menambah **reliability operasional** (risk guardrail + governance monitoring).
- Menjaga **developer velocity** lewat checklist verifikasi harian.

---

## Day 1 — Baseline & Environment Health

### Task
1. Validasi `.env` untuk semua variabel minimum.
2. Jalankan lint + unit test baseline.
3. Snapshot metrik awal backtest/tuning/walk-forward/reliability.

### Command
```bash
python -m ruff check .
python -m pytest -q
python -m agent.main --backtest-file tests/data/backtest_sample.csv
python -m agent.main --tune-file tests/data/backtest_sample.csv
python -m agent.main --walk-forward-file tests/data/backtest_sample.csv --wf-train-size 3 --wf-test-size 1
python -m agent.main --reliability-file tests/data/backtest_sample.csv --reliability-window 20
```

### Acceptance Criteria
- Semua command sukses.
- Metrik baseline terdokumentasi untuk pembanding.

---

## Day 2 — Live Executor Contract Audit

### Task
1. Audit endpoint `submit/cancel/status` pada `LiveCLOBExecutor`.
2. Petakan status mapping real API vs internal `OrderStatus`.
3. Tambah test kontrak untuk shape payload/response edge-case.

### Acceptance Criteria
- Mapping status terdefinisi jelas.
- Tidak ada ambiguity pada skenario `HTTP_ERROR/NETWORK_ERROR/TIMEOUT`.

---

## Day 3 — Streaming Ingestion Skeleton

### Task
1. Tambah skeleton WebSocket ingestion (non-breaking, opt-in).
2. Fallback otomatis ke REST jika stream disconnect.
3. Simpan snapshot event minimal untuk debugging.

### Acceptance Criteria
- Stream bisa nyala/mati tanpa merusak alur existing.
- Keputusan agent tetap berjalan saat stream off.

---

## Day 4 — Portfolio Risk Guardrails

### Task
1. Tambah limit exposure lintas market/event category.
2. Tambah daily loss limit + kill switch.
3. Pastikan guardrail tercermin di rationale keputusan.

### Acceptance Criteria
- Saat threshold risk terlampaui, signal otomatis HOLD/de-risk.
- Ada unit test untuk semua guardrail baru.

---

## Day 5 — Governance Automation

### Task
1. Buat script scheduler untuk run backtest/tuning/walk-forward/reliability periodik.
2. Simpan output metrik historis untuk analisis drift.
3. Definisikan ambang alert awal (warning/critical).

### Acceptance Criteria
- Satu command menjalankan keseluruhan governance loop.
- Drift antar run dapat dibaca dari artifact.

---

## Day 6 — Observability & Alert Routing

### Task
1. Perkaya metrik untuk fill quality, circuit breaker frequency, source health drop.
2. Tambah channel notifikasi (minimal webhook stub).
3. Tambah runbook insiden ringan.

### Acceptance Criteria
- Alert penting muncul di satu channel.
- Operator bisa follow runbook tanpa membaca source code.

---

## Day 7 — Paper Soak & Release Gate

### Task
1. Jalankan paper trading soak test.
2. Review error budget dan false signal.
3. Tentukan go/no-go checklist untuk live rollout kecil.

### Acceptance Criteria
- Tidak ada critical failure berulang.
- Checklist release gate terpenuhi.

---

## Deliverables Akhir Minggu
- Improvement code + test coverage guardrail/streaming/gov.
- Artifact metrik harian (baseline vs akhir minggu).
- Keputusan rollout: lanjut live terbatas atau perpanjang hardening.
