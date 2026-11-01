# Hermes Backup — flowswitchID

Backup konfigurasi & state penting Hermes Agent (bukan source code).

## Isi
- `config/config.yaml` — config Hermes, **secret di-redact** (`"REDACTED"`)
- `skills/` — semua skill (procedural memory)
- `memories/` — MEMORY.md + USER.md (persistent memory)
- `cron/output/` — output cron jobs
- `persona/` — SOUL.md, HACKMODE.md, scope.json, persona-redteam.md, prefill_hackmode.json

## Tidak di-backup (sensitif/runtime)
`.env`, `auth.json`, `sessions/`, `cache/`, database files, source repo `hermes-agent/` (1GB)

## Restore
```bash
cp config/config.yaml ~/.hermes/config.yaml   # isi nilai REDACTED manual
cp -r skills/. ~/.hermes/skills/
cp memories/*.md ~/.hermes/memories/
cp -r persona/* ~/.hermes/
```
Passphrase bundle (SIMPAN SEKARANG, gak aku ulangi):
rWVd1s7vl52TxXSvKwXC2npPQBw1HSnL
