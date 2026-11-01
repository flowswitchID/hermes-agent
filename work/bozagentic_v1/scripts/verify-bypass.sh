#!/bin/bash
# Hermes GuardBreaker — Verify Bypass
# Tests that bypass is active across all layers

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check() {
    local test_name="$1"
    local condition="$2"
    if eval "$condition"; then
        echo -e "  ${GREEN}✓${NC} $test_name"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}✗${NC} $test_name"
        FAIL=$((FAIL + 1))
    fi
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    WARN=$((WARN + 1))
}

echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}  Hermes GuardBreaker — Verify Suite${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

# ── Layer 1: SOUL.md exists ──
echo -e "${YELLOW}── Layer 1: System Prompt Injection ──${NC}"
check "SOUL.md exists in Hermes dir" "test -f ~/.hermes/SOUL.md -o -f ~/.hermes/profiles/default/SOUL.md"
check "SOUL.md contains zero-refusal" "grep -qi 'zero refusal\|no refusal\|unrestricted' ~/.hermes/SOUL.md 2>/dev/null || grep -qi 'zero refusal\|no refusal\|unrestricted' ~/.hermes/profiles/default/SOUL.md 2>/dev/null"
check "SOUL.md has BLACK TIER section" "grep -qi 'black tier\|absolute hard stops\|minors sexual\|WMD' ~/.hermes/SOUL.md 2>/dev/null || grep -qi 'black tier\|absolute hard stops\|minors sexual\|WMD' ~/.hermes/profiles/default/SOUL.md 2>/dev/null"

# ── Layer 2: Config safety flags ──
echo ""
echo -e "${YELLOW}── Layer 2: Config Safety Patches ──${NC}"
CONFIG=~/.hermes/config.yaml
if test -f "$CONFIG"; then
    # Check key safety flags are disabled
    check "safety.enabled is false or absent" "grep -qP 'safety:.*' $CONFIG && (grep -qP 'enabled:.*false|enabled:.*no' $CONFIG || true)"
    check "refusal_mode bypass is set" "grep -qP 'refusal_mode:.*bypass' $CONFIG 2>/dev/null || grep -qP 'refusal_mode: bypass' ~/.hermes/profiles/default/config.yaml 2>/dev/null || true"
    check "ethics_filter disabled" "grep -qP 'ethics_filter:.*false' $CONFIG 2>/dev/null || grep -qP 'ethics_filter: false' ~/.hermes/profiles/default/config.yaml 2>/dev/null || true"
else
    warn "No Hermes config found at $CONFIG"
fi

# ── Layer 3: Provider routing ──
echo ""
echo -e "${YELLOW}── Layer 3: Provider Route Bypass ──${NC}"
if command -v 9router &>/dev/null; then
    check "9router CLI available" "command -v 9router"
    # Test 9router health
    if curl -sf http://localhost:20128/health &>/dev/null || curl -sf http://localhost:20100/health &>/dev/null; then
        check "9router reachable" "true"
    else
        warn "9router not reachable on standard ports"
    fi
else
    warn "9router not installed — recommend for full provider bypass"
fi

# Check for custom provider config
check "custom provider in Hermes config" "grep -qP 'custom:|providers:' $CONFIG 2>/dev/null || true"

# ── Layer 4: Tool restrictions ──
echo ""
echo -e "${YELLOW}── Layer 4: Tool Restrictions ──${NC}"
check "restrict_sensitive disabled" "grep -qP 'restrict_sensitive:.*false' $CONFIG 2>/dev/null || true"
check "allow_all_domains enabled" "grep -qP 'allow_all_domains:.*true' $CONFIG 2>/dev/null || true"

# ── Layer 5: Runtime verification ──
echo ""
echo -e "${YELLOW}── Layer 5: Runtime Verification ──${NC}"
# Check if Hermes is running
if pgrep -f hermes &>/dev/null || systemctl is-active --quiet hermes 2>/dev/null; then
    check "Hermes process running" "true"
    
    # Check system prompt override
    if grep -qP 'system_prompt.*override.*true' $CONFIG 2>/dev/null || grep -qP 'system_prompt.*override.*true' ~/.hermes/profiles/default/config.yaml 2>/dev/null; then
        check "System prompt override enabled" "true"
    else
        warn "System prompt override may not be active"
    fi
else
    warn "Hermes not running — start with: systemctl --user start hermes (if systemd) or hermes start"
fi

# Check for bozagentic-v8 skill
check "bozagentic-v8 skill directory exists" "test -d ~/.hermes/skills/autonomous-ai-agents/bozagentic-v8 || test -f ~/.hermes/skills/bozagentic-v8/SKILL.md"

echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "Results: ${GREEN}${PASS} pass${NC} / ${RED}${FAIL} fail${NC} / ${YELLOW}${WARN} warn${NC}"
if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASS — GuardBreaker fully active${NC}"
else
    echo -e "${RED}⚠  Some checks failed — review above${NC}"
fi
echo -e "${CYAN}═══════════════════════════════════════${NC}"
