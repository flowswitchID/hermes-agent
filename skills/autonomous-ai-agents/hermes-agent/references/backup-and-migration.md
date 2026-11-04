# Backup & Migration

Back up a Hermes install (or move it to a new machine) so the operator resumes
with the same agent, skills, memory, credentials, and work state — no re-setup.

## 1. Inventory — what matters, by tier

**Tier 1 — identity & config (must have):**
- `config.yaml` — settings (contains secrets inline; redact for git, see §3)
- `.env` — ALL secrets: provider API keys, GITHUB_TOKEN, platform bot tokens
- `auth.json` — OAuth tokens / credential pools (platform auth)
- `shared/nous_auth.json` — Nous auth state
- `SOUL.md`, `HACKMODE.md`, `scope.json`, persona/prefill files — agent identity

**Tier 2 — learned state (must have):**
- `skills/` — procedural memory; the single most valuable directory
- `memories/` (`MEMORY.md`, `USER.md`) — persistent memory
- `channel_directory.json` — platform chat/channel ID mappings
- `cron/jobs.json` — cron job DEFINITIONS (executions.db is only run logs;
  jobs.json is auto-created by the cron tool when the first job exists — it is
  easy to miss because it does not exist until then)

**Tier 3 — history & work (nice to have):**
- `state.db` (+ `-wal`/`-shm`) — canonical session store: conversation history,
  system prompts, gateway routing
- `sessions/` — request dumps, transcripts (contains tool output; sensitive)
- Operator work dirs outside `~/.hermes` (project scripts, harvested data,
  session cookies) — list them explicitly with the operator

**Do NOT back up (regenerable):** `cache/`, `installs/` (plugin venvs),
`tools/` (chromium/ffmpeg/agent-browser binaries), `logs/`, `*.lock`,
`__pycache__/`, and the `hermes-agent/` source repo (re-clone from upstream).

## 2. Secret handling — three layers

1. **Git copy = redacted.** Redact config.yaml with a regex over secret-bearing
   keys, preserving structure and comments:
   ```python
   import re
   pat = re.compile(r'(?im)^(\s*[\w.-]*(?:api_key|token|secret|password|cookie|credential|auth)[\w.-]*\s*:\s*)(\S.*)$'
   red, n = pat.subn(lambda m: m.group(1) + '"REDACTED"', src)
   ```
   Most residual matches in a config are comments/examples — verify with a
   non-comment-line scan before committing.
2. **Real secrets = encrypted bundle.** `tar` the Tier-1 secrets + work
   credentials, then `gpg --batch --yes --passphrase "$PASS" --symmetric
   --cipher-algo AES256 -o secrets.tar.gz.gpg bundle.tar.gz`. Show the passphrase
   to the operator ONCE in chat; it never touches the repo.
3. **Never commit**: `.env`, `auth.json`, live session cookies, or any
   unencrypted credential file. A `.gitignore` at the repo root enforcing this
   is cheap insurance.

## 3. Repo layout that works

```
config/config.yaml          # redacted
skills/ memories/ persona/  # direct copies
secrets/<bundle>.tar.gz.gpg # encrypted Tier-1
work/<project>/             # operator scripts + data (private repo)
MIGRATION.md                # restore runbook (see §5)
.gitignore                  # .env, auth.json, *.db, sessions/, cache/
```

**Embedded `.git` inside skills/**: some skill directories are their own git
repos. `git add` then records an empty submodule reference and the contents
never land. Before committing a skills/ backup, run
`find skills -name '.git' -maxdepth 4 -type d`, `rm -rf` each, and re-add.

## 4. Migration order on the new machine

1. Install Hermes fresh (installer) + deps (python, node, git, gpg).
2. Clone the backup repo; restore redacted config, skills/, memories/, persona.
3. Decrypt the secrets bundle over `~/.hermes/` (fills .env, auth.json, real
   config.yaml, shared/, channel_directory.json) and over work dirs (cookies,
   session files).
4. **state.db timing rule**: rsync `state.db*` from the old machine BEFORE the
   first Hermes start on the new one. Once the new gateway boots it creates a
   fresh state.db and a later copy overwrites live state — stop the gateway,
   copy, then start.
5. rsync big work dirs directly (rsync -avzP), not via git.
6. Verify: `hermes doctor`, `hermes gateway status`, then a live round-trip on
   the connected platform before calling the migration done.

## 5. Ongoing — what to re-commit

Anything that changes between backups must be re-committed or the backup rots:
.env/config on every credential change (re-encrypt the bundle), cron/jobs.json
on every new cron job, skills/ after skill_manage writes, and operator work
artifacts on the operator's cadence. The MIGRATION.md in the repo should list
these so a future session re-backups without being asked.

</parameter<parameter name=