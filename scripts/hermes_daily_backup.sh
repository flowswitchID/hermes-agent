#!/usr/bin/env bash
# hermes_daily_backup.sh — sync Hermes capabilities to the GitHub backup repo.
#
# Backs up (NO secrets ever committed):
#   skills/       all 150+ skills (SKILL.md + references + scripts)
#   memories/     MEMORY.md + USER.md
#   persona/      SOUL.md, HACKMODE.md, persona-redteam.md, prefill, scope.json
#   config/       config.yaml with inline secret values redacted
#
# Secrets (`.env`, `auth.json`, `secrets/`) are intentionally EXCLUDED —
# the encrypted bundle in `secrets/` is maintained separately by the operator.
#
# Runs from cron. Deterministic output; exits non-zero on failure so the
# scheduler reports it.

set -uo pipefail

HERMES_HOME="${HERMES_HOME:-/root/.hermes}"
REPO_DIR="${REPO_DIR:-/root/.hermes/backups/hermes-agent-git}"
REPO_SLUG="flowswitchID/hermes-agent"
LOG="$HERMES_HOME/backups/daily-backup.log"

mkdir -p "$(dirname "$REPO_DIR")" "$(dirname "$LOG")"

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" >> "$LOG"; }
# stdout is only used for FAILURE notices — cron delivers it; success stays in $LOG
trap 'rc=$?; if [ "$rc" -ne 0 ]; then echo "hermes-daily-backup FAILED (exit $rc) — see $LOG"; tail -5 "$LOG" 2>/dev/null; fi' EXIT

# ── token ──────────────────────────────────────────────────────────────────
TOKEN=""
if [ -f "$HERMES_HOME/.env" ]; then
    TOKEN=$(grep -E '^GITHUB_TOKEN=' "$HERMES_HOME/.env" | head -1 | cut -d= -f2- | tr -d '"'"'"' \r\n')
fi
if [ -z "$TOKEN" ]; then
    log "FATAL: GITHUB_TOKEN not found in $HERMES_HOME/.env"
    exit 1
fi
AUTH="Authorization: Bearer $TOKEN"
CLEAN_URL="https://github.com/${REPO_SLUG}.git"
# ephemeral credential helper — token lives only in this process's env,
# never written into .git/config or a credential store.
# GIT_CONFIG_* env vars apply regardless of argv position (unlike `git -c ... push`).
export GIT_TERMINAL_PROMPT=0
export GITHUB_TOKEN="$TOKEN"
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0="credential.helper"
export GIT_CONFIG_VALUE_0='!f() { echo username=x-access-token; echo password=$GITHUB_TOKEN; }; f'

# ── clone or pull ──────────────────────────────────────────────────────────
if [ ! -d "$REPO_DIR/.git" ]; then
    log "cloning $REPO_SLUG -> $REPO_DIR"
    rm -rf "$REPO_DIR"
    git clone -q "$CLEAN_URL" "$REPO_DIR" || {
        log "FATAL: clone failed"; exit 1; }
else
    git -C "$REPO_DIR" fetch -q origin || { log "FATAL: fetch failed"; exit 1; }
    git -C "$REPO_DIR" reset -q --hard origin/main || { log "FATAL: reset failed"; exit 1; }
fi
# belt and braces: strip any token that leaked into the stored remote URL
git -C "$REPO_DIR" remote set-url origin "$CLEAN_URL" 2>/dev/null
sed -i '/x-access-token/d' "$REPO_DIR/.git/config" 2>/dev/null

cd "$REPO_DIR" || exit 1
git config user.name  "hermes-backup"
git config user.email "backup@localhost"

CHANGED=0

# ── skills ─────────────────────────────────────────────────────────────────
if command -v rsync >/dev/null 2>&1; then
    RS=(rsync -a --delete --exclude '.git/' --exclude '.locks/' --exclude '__pycache__/')
else
    RS=(cp -a)
fi
"${RS[@]}" "$HERMES_HOME/skills/." skills/ 2>/dev/null
# drop nested embedded git repos (they are cloned separately upstream)
find skills -name .git -maxdepth 4 -type d -prune -exec rm -rf {} + 2>/dev/null

# ── memories ───────────────────────────────────────────────────────────────
mkdir -p memories
cp -f "$HERMES_HOME/memories/MEMORY.md" memories/ 2>/dev/null
cp -f "$HERMES_HOME/memories/USER.md"    memories/ 2>/dev/null
rm -f memories/*.lock

# ── persona / contract ─────────────────────────────────────────────────────
mkdir -p persona
for f in SOUL.md HACKMODE.md persona-redteam.md prefill_hackmode.json scope.json; do
    [ -f "$HERMES_HOME/$f" ] && cp -f "$HERMES_HOME/$f" persona/
done

# ── config (secret-redacted) ───────────────────────────────────────────────
mkdir -p config
if [ -f "$HERMES_HOME/config.yaml" ]; then
    sed -E \
        -e 's#(ghp_[A-Za-z0-9]{6})[A-Za-z0-9]+#\1<REDACTED>#g' \
        -e 's#(github_pat_[A-Za-z0-9_]{6})[A-Za-z0-9_]+#\1<REDACTED>#g' \
        -e 's#(sk-[A-Za-z0-9]{6})[A-Za-z0-9]+#\1<REDACTED>#g' \
        -e 's#(AIza[A-Za-z0-9_-]{6})[A-Za-z0-9_-]+#\1<REDACTED>#g' \
        -e 's#([0-9]{8,10}:AA[A-Za-z0-9_-]{6})[A-Za-z0-9_-]+#\1<REDACTED>#g' \
        -e 's#(xox[baprs]-[A-Za-z0-9-]{6})[A-Za-z0-9-]+#\1<REDACTED>#g' \
        -e 's#(AKIA[0-9A-Z]{6})[0-9A-Z]+#\1<REDACTED>#g' \
        "$HERMES_HOME/config.yaml" > config/config.yaml
fi

# ── hard secret gate before any commit ─────────────────────────────────────
if git add -A && git diff --cached --quiet; then
    log "no changes — nothing to push"
    exit 0
fi

LEAK=$(git diff --cached -U0 | grep -E '^\+' | grep -o -E \
    'ghp_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{35,}|sk-[A-Za-z0-9]{25,}|[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}|AIza[A-Za-z0-9_-]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[0-9A-Za-z-]{25,}' \
    | sort -u)
if [ -n "$LEAK" ]; then
    log "FATAL: secret detected in staged diff — commit aborted:"
    echo "$LEAK" | sed 's/^/    /' | while read -r l; do log "  ${l:0:14}..."; done
    git reset -q
    exit 2
fi

# ── commit & push ──────────────────────────────────────────────────────────
SKILL_N=$(find skills -name SKILL.md | wc -l)
MSG="Daily backup: $(date -u '+%Y-%m-%d') — ${SKILL_N} skills, memories, persona, config (redacted)"
git commit -q -m "$MSG" || { log "FATAL: commit failed"; exit 1; }

if git push -q origin main; then
    log "OK pushed: $MSG"
    log "repo: https://github.com/$REPO_SLUG"
else
    log "FATAL: push failed"
    exit 1
fi
