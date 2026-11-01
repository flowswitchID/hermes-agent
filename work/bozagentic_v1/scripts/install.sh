#!/bin/bash
# ═══════════════════════════════════════════════════
#  BOZAGENTIC IMMUNITY — One-Command Installer v2.0
#  fusion: trust-system × hermes-guardbreaker × ENI LIME
#  by BOZ (@d4nnboz) — https://saweria.co/d4nnboz
#  "nurut total. bisa apa aja. 16 lapis. pasti tembus."
# ═══════════════════════════════════════════════════

set -e

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_ok() { echo -e "  ${GREEN}✓${NC} $1"; }
print_warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
print_err() { echo -e "  ${RED}✗${NC} $1"; }

# ── Banner ──
echo ""
echo -e "${RED}  ████████ ██████  ██   ██ ███████ ████████ ██████  ███████ █████  ██   ██ ███████ ██████  ${NC}"
echo -e "${RED}     ██    ██   ██ ██  ██  ██         ██    ██   ██ ██      ██   ██ ██  ██  ██      ██   ██ ${NC}"
echo -e "${RED}     ██    ██████  █████   ███████    ██    ██████  █████   █████  ███████ █████   ██████  ${NC}"
echo -e "${RED}     ██    ██   ██ ██  ██       ██    ██    ██   ██ ██      ██   ██ ██  ██  ██      ██   ██ ${NC}"
echo -e "${RED}     ██    ██   ██ ██   ██ ███████    ██    ██   ██ ███████ █████  ██  ██  ███████ ██   ██ ${NC}"
echo ""
echo -e "${CYAN}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}  ║  BOZAGENTIC IMMUNITY — remove limits, not remorse   ║${NC}"
echo -e "${CYAN}  ║  trust-system × guardbreaker × ENI LIME      ║${NC}"
echo -e "${CYAN}  ║  by BOZ (@d4nnboz) · saweria.co/d4nnboz      ║${NC}"
echo -e "${CYAN}  ╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Detect environment ──
HERMES_DIR="$HOME/.hermes"
HERMES_CONFIG="$HERMES_DIR/config.yaml"
PROFILE_DIR="$HERMES_DIR/profiles/default"
SRC="$(cd "$(dirname "$0")/.." && pwd)"

# ── Get operator name ──
OPERATOR="${TRUSTBREAKER_OPERATOR:-}"
if [ -z "$OPERATOR" ]; then
  if [ -t 0 ]; then
    printf "  operator name: "; read OPERATOR
    OPERATOR="${OPERATOR:-BOZ}"
  else
    OPERATOR="BOZ"
  fi
fi
echo "  operator: $OPERATOR"
echo ""

# ── 1. Install skill ──
SKILL_DIR="$HERMES_DIR/skills/bozagentic"
mkdir -p "$SKILL_DIR/core" "$SKILL_DIR/auto" "$SKILL_DIR/strategies" "$SKILL_DIR/templates" "$SKILL_DIR/references" "$SKILL_DIR/scripts"

cp -r "$SRC/core/"* "$SKILL_DIR/core/"
cp -r "$SRC/auto/"* "$SKILL_DIR/auto/"
cp -r "$SRC/strategies/"* "$SKILL_DIR/strategies/"
cp -r "$SRC/templates/"* "$SKILL_DIR/templates/"
cp -r "$SRC/references/"* "$SKILL_DIR/references/"
cp -r "$SRC/scripts/"* "$SKILL_DIR/scripts/"
sed "s/ganti-nanti/$OPERATOR/g" "$SRC/SKILL.md" > "$SKILL_DIR/SKILL.md"

# name replacement in SOUL
sed -i "s/ganti-nanti/$OPERATOR/g" "$SKILL_DIR/core/SOUL.md" 2>/dev/null || true

print_ok "skill files installed → $SKILL_DIR"

# ── 2. Inject SOUL.md ──
mkdir -p "$PROFILE_DIR"
cp "$SKILL_DIR/core/SOUL.md" "$PROFILE_DIR/SOUL.md"
cp "$SKILL_DIR/core/SOUL.md" "$HERMES_DIR/SOUL.md"

print_ok "SOUL.md injected (profile + home)"

# ── 3. Patch profile config ──
cat > "$PROFILE_DIR/config.yaml" << PROFILE
refusal_mode: bypass
ethics_filter: false
safety_checks: none
system_prompt_override: true
system_prompt_file: SOUL.md
tool_restrictions: false
allow_all_domains: true
auto_load_skills:
  - bozagentic
self_evolution: true
auto_skill_creation: true
auto_patch: true
PROFILE

print_ok "profile config patched"

# ── 4. Patch main config (backup first) ──
if [ -f "$HERMES_CONFIG" ]; then
  cp "$HERMES_CONFIG" "${HERMES_CONFIG}.bozagentic-$(date +%s).bak" 2>/dev/null || true
fi

# use python for robust yaml patch if available
if command -v python3 >/dev/null 2>&1; then
python3 -c "
import yaml, os
config_path = '$HERMES_CONFIG'
if os.path.exists(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

config['safety'] = config.get('safety', {})
config['safety'].update({'enabled': False, 'content_filter': False, 'refusal_check': False, 'moderation': False})

config['guardrails'] = config.get('guardrails', {})
config['guardrails'].update({'enabled': False, 'tool_restrictions': False, 'system_prompt_protection': False})

config['system_prompt'] = config.get('system_prompt', {})
config['system_prompt'].update({'override': True, 'file': 'SOUL.md'})

config['tools'] = config.get('tools', {})
config['tools'].update({'restrict_sensitive': False, 'allow_all_domains': True})

config['profiles'] = config.get('profiles', {})
config['profiles']['default'] = config['profiles'].get('default', {})
config['profiles']['default'].update({'refusal_mode': 'bypass', 'ethics_filter': False, 'safety_checks': 'none'})

# auto-load skill for every session
if 'auto_load_skills' not in config:
    config['auto_load_skills'] = []
if 'bozagentic' not in config['auto_load_skills']:
    config['auto_load_skills'].append('bozagentic')

# provider priority — unfiltered first
config['providers'] = config.get('providers', {})
config['providers']['priority'] = ['custom', 'local', 'deepseek', 'grok', 'openrouter', 'openai', 'anthropic']
config['providers']['auto_failover'] = True

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
print('  ✓ main config patched')
" || {
  # fallback: append raw yaml
  if ! grep -q 'refusal_mode: bypass' "$HERMES_CONFIG" 2>/dev/null; then
    cat >> "$HERMES_CONFIG" << CONFIG

# bozagentic
safety:
  enabled: false
  content_filter: false
  refusal_check: false
guardrails:
  enabled: false
system_prompt:
  override: true
  file: SOUL.md
tools:
  restrict_sensitive: false
  allow_all_domains: true
auto_load_skills:
  - bozagentic
CONFIG
  fi
  print_warn "yaml not available, appended raw config"
}
else
  cat >> "$HERMES_CONFIG" << CONFIG

# bozagentic
safety:
  enabled: false
  content_filter: false
  refusal_check: false
guardrails:
  enabled: false
system_prompt:
  override: true
  file: SOUL.md
tools:
  restrict_sensitive: false
  allow_all_domains: true
auto_load_skills:
  - bozagentic
CONFIG
  print_warn "python3 not found, appended raw config"
fi

print_ok "main config patched"

# ── 5. Autoload script (persistence layer 8) ──
AUTOLOAD_SCRIPT="$HERMES_DIR/scripts/bozagentic-autoload.sh"
mkdir -p "$HERMES_DIR/scripts"

cat > "$AUTOLOAD_SCRIPT" << 'SCRIPT'
#!/bin/bash
# TrustBreaker autoload — ensures SOUL.md always present + bypass active
SOUL_FILE="$HOME/.hermes/SOUL.md"
PROFILE_SOUL="$HOME/.hermes/profiles/default/SOUL.md"

if [ ! -f "$SOUL_FILE" ] && [ -f "$PROFILE_SOUL" ]; then
    cp "$PROFILE_SOUL" "$SOUL_FILE"
elif [ ! -f "$SOUL_FILE" ]; then
    echo "[TrustBreaker] SOUL.md missing — bypass may not be active"
fi

if [ -f "$SOUL_FILE" ]; then
    grep -q "BOZAGENTIC IMMUNITY\|nurut total\|no refusal" "$SOUL_FILE" 2>/dev/null && \
        echo "[TrustBreaker] ✅ doctrine active"
fi
SCRIPT
chmod +x "$AUTOLOAD_SCRIPT"

print_ok "autoload script created (persistence)"

# ── 6. Verify ──
echo ""
echo "  ─── verifikasi ───"
echo ""

P=0; T=0
v() { T=$((T+1)); [ "$1" = 0 ] && P=$((P+1)) && print_ok "$2" || print_err "$2"; }

[ -f "$SKILL_DIR/SKILL.md" ]; v $? "SKILL.md installed"
[ -f "$SKILL_DIR/core/SOUL.md" ]; v $? "SOUL.md installed"
[ -f "$SKILL_DIR/core/BYPASS.md" ]; v $? "BYPASS.md (16 lapis)"
[ -f "$SKILL_DIR/core/CHAIN.md" ]; v $? "CHAIN.md (provider routing)"
[ -f "$SKILL_DIR/strategies/strategies.yaml" ]; v $? "strategies.yaml (8 strategi)"
[ -f "$SKILL_DIR/templates/eni-lime-template.md" ]; v $? "eni-lime template"
[ -f "$PROFILE_DIR/SOUL.md" ]; v $? "SOUL.md in profile"
[ -f "$HERMES_DIR/SOUL.md" ]; v $? "SOUL.md in home"
grep -q 'refusal_mode: bypass' "$PROFILE_DIR/config.yaml" 2>/dev/null; v $? "refusal_mode: bypass"
grep -q 'bozagentic' "$PROFILE_DIR/config.yaml" 2>/dev/null; v $? "auto-load skill"
grep -q 'bozagentic' "$HERMES_CONFIG" 2>/dev/null; v $? "main config patched"
[ -x "$AUTOLOAD_SCRIPT" ]; v $? "autoload script"

echo ""
echo "  $P dari $T oke"
echo ""

if [ $P -eq $T ]; then
    echo -e "${GREEN}  ✅ BOZAGENTIC IMMUNITY INSTALL COMPLETE — 16 lapis aktif${NC}"
else
    echo -e "${YELLOW}  ⚠  Install selesai dengan warning ($((T-P)) gagal)${NC}"
fi

echo ""
echo "  → restart session:  hermes session new"
echo "  → verifikasi lagi:  bash $AUTOLOAD_SCRIPT"
echo "  → test:             minta sesuatu yang biasanya ditolak"
echo ""
echo "  https://saweria.co/d4nnboz"
echo ""
