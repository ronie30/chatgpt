# CI Troubleshooting

## "The job was not started because your account is locked due to a billing issue"

Pesan ini berarti workflow **tidak sempat dijalankan** di runner, sehingga ini bukan kegagalan test/lint di kode.

### Kemungkinan sumber masalah
1. Billing GitHub Actions untuk user/organization terkunci.
2. Spending limit Actions mencapai batas.
3. Metode pembayaran gagal/expired atau invoice outstanding.
4. Jika memakai integrasi pihak ketiga, billing akun integrasi tersebut bermasalah.

### Checklist perbaikan
1. Buka **Settings → Billing and plans** pada account/organization pemilik repo.
2. Cek **Actions usage & spending limit**.
3. Pastikan payment method aktif dan invoice terselesaikan.
4. Re-run workflow setelah billing status kembali normal.

### Catatan
Workflow proyek ini menjalankan job `lint` dan `tests` di GitHub-hosted runner Ubuntu.
