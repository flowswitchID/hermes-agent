# Hermes Migration Runbook — VPS Baru

Runbook lengkap pindah Hermes ke VPS baru tanpa setup ulang dari nol.

## Isi repo backup

| Path | Isi | Sensitif? |
|---|---|---|
| `config/config.yaml` | config Hermes | secret di-redact |
| `skills/` | semua skill | aman |
| `memories/` | MEMORY.md + USER.md | aman |
| `persona/` | SOUL, HACKMODE, scope.json, prefill | aman |
| `secrets/hermes_secrets.tar.gz.gpg` | **bundle terenkripsi**: `.env`, `auth.json`, `config.yaml` asli, `shared/nous_auth.json`, `channel_directory.json`, `cookies_google.json`, `jio_sessions/` | ENKRIPSI AES256 |
| `work/jio_farm/` | script farm + hasil (links, results, used numbers, panels) | semi-sensitif (repo private) |
| `cron/jobs.json` | definisi cron job (kalau ada) | aman |

## Langkah migrasi

### 1. VPS baru — install Hermes
```bash
# install Hermes Agent (Nous Research) sesuai dokumentasi resmi
# pastikan python 3.11+, node (buat browser tools), git, gpg
```

### 2. Restore file non-rahasia
```bash
git clone https://github.com/flowswitchID/hermes-agent.git /tmp/hermes-backup
cd /tmp/hermes-backup

# config (isikan nilai REDACTED manual ATAU pakai bundle secrets di step 3)
cp config/config.yaml ~/.hermes/config.yaml

# skills
cp -r skills/. ~/.hermes/skills/

# memories
cp memories/MEMORY.md memories/USER.md ~/.hermes/memories/

# persona & hackmode
cp persona/* ~/.hermes/

# work project
mkdir -p ~/jio_farm && cp -r work/jio_farm/. ~/jio_farm/
```

### 3. Restore secrets (bundle terenkripsi)
```bash
gpg --batch --yes --passphrase "PASSPHRASE_LO" \
    --decrypt secrets/hermes_secrets.tar.gz.gpg > /tmp/secrets.tar.gz
tar xzf /tmp/secrets.tar.gz -C ~/.hermes/
# isi bundle: .env, auth.json, config.yaml (asli), shared/nous_auth.json,
#             channel_directory.json
tar xzf /tmp/secrets.tar.gz -C ~/jio_farm/   # cookies_google.json + jio_sessions/
```
> Passphrase bundle disimpan operator (password manager). Kalau hilang: `.env` +
> `auth.json` + `config.yaml` harus dibuat ulang manual (re-pair Telegram, re-isi API key).

### 4. Cron jobs
```bash
# kalau dulu pernah bikin cron job:
cp cron/jobs.json ~/.hermes/cron/jobs.json
# (file ini auto-dibuat Hermes saat cronjob_manage dipakai; backup tiap ada job baru)
```

### 5. Verifikasi
```bash
hermes doctor          # cek kesehatan install
hermes gateway status  # cek gateway (Telegram dll)
# test: kirim pesan ke bot Telegram → harusnya reply
cd ~/jio_farm && python3 myjio.py --help   # farm script jalan
```

## Yang TIDAK di-backup (regenerate/install ulang)

- `cache/`, `installs/` (venv plugin) — auto-download
- `tools/` (chromium, ffmpeg, agent-browser) — auto-download
- `logs/`, `sessions/` (request dumps) — runtime
- `state.db` — **history chat (14 sesi, 3218 pesan)**. Kalau mau ikut: rsync manual
  `state.db` + `state.db-*` dari VPS lama SEBELUM Hermes pertama kali start di VPS baru
  (kalau sudah start, Hermes bikin state.db baru — timpa manual sementara gateway mati).
- Source repo `hermes-agent/` (1 GB) — re-clone dari upstream
- MoneyPrinterTurbo (2.1 GB) & REA toolkit (1.2 GB) — rsync manual kalau masih dipakai

## catatan: file yang harus di-backup ulang tiap ada perubahan

- `.env` / `config.yaml` tiap ganti provider/API key → re-encrypt bundle
- `cron/jobs.json` tiap bikin cron job baru
- `work/jio_farm/` telaah berkala (mikirdekbot_activation_links.txt bertambah)
- skills baru (via skill_manage) → commit ke repo
