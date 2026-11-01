#!/bin/bash
# ============================================================
# SETUP-VPS.sh — 1 command, semua audit tools ter-install
# Usage: bash setup-vps.sh
# Tested: Ubuntu 22.04/24.04, Debian 12
# ============================================================

set -e
echo "============================================================"
echo "  BOZAGENTIC v7 — VPS SETUP"
echo "  Installing all 30 audit tools..."
echo "============================================================"
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

ok() { echo -e "  ${GREEN}✅ $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; }

# ============================================================
# 1. SYSTEM DEPS
# ============================================================
echo "[1/8] System dependencies..."
apt-get update -qq && apt-get install -y -qq \
    python3 python3-pip python3-venv \
    git curl wget unzip jq \
    build-essential pkg-config libssl-dev \
    > /dev/null 2>&1
ok "System deps"

# ============================================================
# 2. FOUNDRY (forge, cast, anvil)
# ============================================================
echo "[2/8] Foundry..."
if ! command -v forge &>/dev/null; then
    curl -L https://foundry.paradigm.xyz 2>/dev/null | bash 2>/dev/null
    export PATH="$HOME/.foundry/bin:$PATH"
    foundryup 2>/dev/null
    # Add to bashrc
    grep -q "foundry/bin" ~/.bashrc 2>/dev/null || echo 'export PATH="$HOME/.foundry/bin:$PATH"' >> ~/.bashrc
fi
export PATH="$HOME/.foundry/bin:$PATH"
forge --version > /dev/null 2>&1 && ok "Foundry $(forge --version 2>&1 | head -1)" || fail "Foundry"

# ============================================================
# 3. PYTHON TOOLS (Slither, Semgrep, Mythril, Halmos, Z3, web3)
# ============================================================
echo "[3/8] Python audit tools..."
pip install --quiet --break-system-packages \
    slither-analyzer \
    semgrep \
    mythril \
    halmos \
    z3-solver \
    web3 \
    solc-select \
    crytic-compile \
    2>/dev/null || pip install --quiet \
    slither-analyzer \
    semgrep \
    mythril \
    halmos \
    z3-solver \
    web3 \
    solc-select \
    crytic-compile \
    2>/dev/null

slither --version > /dev/null 2>&1 && ok "Slither" || fail "Slither"
semgrep --version > /dev/null 2>&1 && ok "Semgrep" || fail "Semgrep"
python3 -m mythril version > /dev/null 2>&1 && ok "Mythril" || fail "Mythril"
halmos --version > /dev/null 2>&1 && ok "Halmos" || fail "Halmos"
python3 -c "import z3; print(z3.get_version_string())" > /dev/null 2>&1 && ok "Z3 $(python3 -c 'import z3; print(z3.get_version_string())')" || fail "Z3"
python3 -c "import web3" > /dev/null 2>&1 && ok "web3.py" || fail "web3.py"

# ============================================================
# 4. SOLC VERSIONS (lokal, no DNS needed at runtime)
# ============================================================
echo "[4/8] Solc versions..."
solc-select install 0.8.29 2>/dev/null && solc-select use 0.8.29 2>/dev/null
solc-select install 0.8.26 2>/dev/null
solc-select install 0.8.23 2>/dev/null
# Also register with solcx (Mythril uses this)
python3 -c "
import solcx
for v in ['0.8.29','0.8.26','0.8.23']:
    try: solcx.install_solc(v)
    except: pass
" 2>/dev/null
ok "Solc $(python3 -c 'import solcx; print(solcx.get_installed_solc_versions())' 2>/dev/null)"

# ============================================================
# 5. ECHIDNA
# ============================================================
echo "[5/8] Echidna..."
if ! command -v echidna &>/dev/null; then
    ECHIDNA_VER=$(curl -s https://api.github.com/repos/crytic/echidna/releases/latest | jq -r '.tag_name' 2>/dev/null || echo "v2.2.6")
    wget -q "https://github.com/crytic/echidna/releases/download/${ECHIDNA_VER}/echidna-${ECHIDNA_VER}-linux-x86_64.tar.gz" -O /tmp/echidna.tar.gz 2>/dev/null
    tar -xzf /tmp/echidna.tar.gz -C /usr/local/bin/ 2>/dev/null
    rm -f /tmp/echidna.tar.gz
fi
echidna --version > /dev/null 2>&1 && ok "Echidna $(echidna --version 2>&1)" || fail "Echidna"

# ============================================================
# 6. MEDUSA
# ============================================================
echo "[6/8] Medusa..."
if ! command -v medusa &>/dev/null; then
    MEDUSA_VER=$(curl -s https://api.github.com/repos/crytic/medusa/releases/latest | jq -r '.tag_name' 2>/dev/null || echo "v1.5.1")
    wget -q "https://github.com/crytic/medusa/releases/download/${MEDUSA_VER}/medusa-linux-x64.tar.gz" -O /tmp/medusa.tar.gz 2>/dev/null
    tar -xzf /tmp/medusa.tar.gz -C /usr/local/bin/ 2>/dev/null
    rm -f /tmp/medusa.tar.gz
fi
medusa --version > /dev/null 2>&1 && ok "Medusa $(medusa --version 2>&1)" || fail "Medusa"

# ============================================================
# 7. ADERYN
# ============================================================
echo "[7/8] Aderyn..."
if ! command -v aderyn &>/dev/null; then
    # Try binary first (faster than cargo)
    ADERYN_VER=$(curl -s https://api.github.com/repos/Cyfrin/aderyn/releases/latest | jq -r '.tag_name' 2>/dev/null || echo "")
    if [ -n "$ADERYN_VER" ]; then
        wget -q "https://github.com/Cyfrin/aderyn/releases/download/${ADERYN_VER}/aderyn-x86_64-unknown-linux-gnu.tar.gz" -O /tmp/aderyn.tar.gz 2>/dev/null && \
        tar -xzf /tmp/aderyn.tar.gz -C /usr/local/bin/ 2>/dev/null && \
        rm -f /tmp/aderyn.tar.gz
    fi
    # Fallback: cargo install
    if ! command -v aderyn &>/dev/null; then
        if command -v cargo &>/dev/null; then
            cargo install aderyn --quiet 2>/dev/null
        else
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y 2>/dev/null
            source "$HOME/.cargo/env" 2>/dev/null
            cargo install aderyn --quiet 2>/dev/null
        fi
    fi
fi
aderyn --version > /dev/null 2>&1 && ok "Aderyn $(aderyn --version 2>&1)" || fail "Aderyn (install manually: cargo install aderyn)"

# ============================================================
# 8. NODE.JS + ETHERS (for on-chain drills)
# ============================================================
echo "[8/8] Node.js + ethers.js..."
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi
node --version > /dev/null 2>&1 && ok "Node $(node --version)" || fail "Node.js"

# ============================================================
# VERIFY ALL
# ============================================================
echo
echo "============================================================"
echo "  VERIFICATION"
echo "============================================================"
TOOLS=(
    "forge:Foundry"
    "slither:Slither"
    "semgrep:Semgrep"
    "echidna:Echidna"
    "medusa:Medusa"
    "aderyn:Aderyn"
    "halmos:Halmos"
    "node:Node.js"
)
PASS=0
TOTAL=${#TOOLS[@]}
for entry in "${TOOLS[@]}"; do
    cmd="${entry%%:*}"
    name="${entry##*:}"
    if command -v "$cmd" &>/dev/null; then
        ((PASS++))
        echo -e "  ${GREEN}✅ $name${NC}"
    else
        echo -e "  ${RED}❌ $name${NC}"
    fi
done

# Python-only tools
for mod in mythril z3 web3; do
    if python3 -c "import $mod" 2>/dev/null; then
        ((PASS++))
        echo -e "  ${GREEN}✅ $mod (python)${NC}"
    else
        echo -e "  ${RED}❌ $mod (python)${NC}"
    fi
done
((TOTAL+=3))

echo
echo "  $PASS/$TOTAL tools installed"
echo
if [ $PASS -eq $TOTAL ]; then
    echo -e "  ${GREEN}✅ ALL TOOLS READY — run-all-tools.sh will work${NC}"
else
    echo -e "  ${RED}⚠️ Some tools missing — check above${NC}"
fi
echo
echo "  Next steps:"
echo "    1. Unzip BOZAGENTIC-v7-LIGHT.zip to ~/.hermes/bozagentic-v7/"
echo "    2. export PATH=\"\$HOME/.foundry/bin:\$PATH\""
echo "    3. ./tools/run-all-tools.sh /path/to/target"
echo
echo "============================================================"
