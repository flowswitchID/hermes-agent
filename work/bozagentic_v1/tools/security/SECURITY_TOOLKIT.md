# SECURITY TOOLKIT + LIBRARY MASTER REFERENCE
# Solmate · PRB-Math · BoringSolidity · Slither · Mythril · Echidna
# BOZAGENTIC · 2026-07-29

---

## 1. SOLMATE v6.8.0 (transmissions11)

**Filosofi:** Gas-optimized, minimal, assembly-heavy. Buat protocol yang butuh every gas unit.

### 1.1 ERC20 (solmate vs OZ)

| Aspek | Solmate | OpenZeppelin |
|-------|---------|--------------|
| Size | 206 lines | 305 lines |
| Gas | Lebih murah (unchecked, no custom errors) | Lebih mahal (checks, custom errors) |
| Safety | ⚠️ NO zero-address checks | ✅ Zero-address checks |
| Permit | Built-in EIP-2612 | Separate extension |
| Domain sep | Cached (INITIAL_CHAIN_ID) | Recomputed |
| Pattern | Direct storage manipulation | `_update()` hook pattern |
| decimals | `immutable` (constructor) | `virtual` (override) |

**Solmate ERC20 — key differences:**
```solidity
// NO zero-address check on transfer — gas saving tapi risky
function transfer(address to, uint256 amount) public virtual returns (bool) {
    balanceOf[msg.sender] -= amount;  // underflow = revert (0.8+)
    unchecked { balanceOf[to] += amount; }  // safe: sum <= totalSupply
    emit Transfer(msg.sender, to, amount);
    return true;
}

// Permit built-in, domain separator CACHED
uint256 internal immutable INITIAL_CHAIN_ID;
bytes32 internal immutable INITIAL_DOMAIN_SEPARATOR;
function DOMAIN_SEPARATOR() public view returns (bytes32) {
    return block.chainid == INITIAL_CHAIN_ID ? INITIAL_DOMAIN_SEPARATOR : computeDomainSeparator();
}
```

**⚠️ Audit note:** Solmate ERC20 nggak cek `to == address(0)`. Transfer ke zero address = burn tokens tanpa event burn. Ini BY DESIGN (gas) tapi bisa jadi bug kalau developer nggak aware.

### 1.2 SafeTransferLib (solmate)

```solidity
library SafeTransferLib {
    function safeTransferETH(address to, uint256 amount) internal;
    function safeTransferFrom(ERC20 token, address from, address to, uint256 amount) internal;
    function safeTransfer(ERC20 token, address to, uint256 amount) internal;
    function safeApprove(ERC20 token, address to, uint256 amount) internal;
}
```

**vs OZ SafeERC20:**
- Solmate: pure assembly, hardcoded selectors, dirty bits warning
- OZ: assembly + high-level, forceApprove (USDT compat), ERC1363 support
- Solmate LEBIH murah gas, OZ LEBIH complete

**Assembly pattern (sama di semua 3 fungsi):**
```solidity
success := call(gas(), token, 0, freeMemoryPointer, calldataLen, 0, 32)
// Check: return == 1 OR (returndata empty AND token has code)
if and(iszero(and(eq(mload(0), 1), gt(returndatasize(), 31))), success) {
    success := iszero(or(iszero(extcodesize(token)), returndatasize()))
}
```

### 1.3 FixedPointMathLib

```solidity
library FixedPointMathLib {
    uint256 constant WAD = 1e18;
    function mulWadDown(uint256 x, uint256 y) → (x * y) / 1e18
    function mulWadUp(uint256 x, uint256 y)   → ceil((x * y) / 1e18)
    function divWadDown(uint256 x, uint256 y) → (x * 1e18) / y
    function divWadUp(uint256 x, uint256 y)   → ceil((x * 1e18) / y)
    function mulDivDown(x, y, d) → (x * y) / d (overflow-safe via assembly)
    function mulDivUp(x, y, d)   → ceil((x * y) / d)
    function rpow(x, n, scalar)  → x^n with rounding (exponentiation by squaring)
    function sqrt(x)             → Babylonian method, 7 iterations
    function unsafeMod(x, y)     → mod without revert on y=0
    function unsafeDiv(x, y)     → div without revert on y=0
}
```

**⚠️ Audit note:** `unsafeDiv` dan `unsafeMod` return 0 kalau y=0 (bukan revert). Kalau protocol pake ini tanpa check → division by zero = silent 0.

### 1.4 ReentrancyGuard (solmate)

```solidity
abstract contract ReentrancyGuard {
    uint256 private locked = 1;  // 19 lines total. That's it.
    modifier nonReentrant() virtual {
        require(locked == 1, "REENTRANCY");
        locked = 2;
        _;
        locked = 1;
    }
}
```

**vs OZ:** OZ pake ERC-7201 namespaced storage + custom error + view modifier. Solmate: 1 slot, string revert. Solmate lebih murah deploy (slot initialized to 1 vs OZ constructor).

### 1.5 Other Solmate Modules

| Module | Key Feature |
|--------|-------------|
| **ERC4626** | Minimal vault, NO virtual shares (⚠️ donation attack vulnerable!) |
| **ERC721** | Gas-optimized, no Enumerable extension |
| **ERC1155** | Minimal multi-token |
| **WETH** | Standard wrapped ETH |
| **Owned** | `owner = msg.sender`, `transferOwnership(address)` — NO 2-step |
| **Auth** | Role-based with `Authority` interface |
| **RolesAuthority** | Role → function mapping per contract |
| **MultiRolesAuthority** | Multi-role with function-level permissions |
| **CREATE3** | Deploy to address independent of bytecode |
| **SSTORE2** | Store data as contract code (cheaper than SSTORE for large data) |
| **MerkleProofLib** | Compatible with OZ MerkleProof |
| **LibString** | String utilities (toString, toHexString) |
| **SafeCastLib** | Safe downcasting |
| **SignedWadMath** | Signed 18-decimal fixed-point |
| **Bytes32AddressLib** | bytes32 ↔ address conversion |

**⚠️ CRITICAL: Solmate ERC4626 TIDAK punya virtual shares mitigation.**
OZ v4.9+ punya `+1` di totalAssets dan `+10^offset` di totalSupply. Solmate nggak. Ini bikin donation attack PROFITABLE di Solmate ERC4626.

---

## 2. PRB-MATH v4.1.2 (PaulRBerg)

**Filosofi:** Fixed-point math library. 18-decimal precision. Type-safe via custom types.

### 2.1 Number Types

| Type | Range | Precision | Use Case |
|------|-------|-----------|----------|
| **UD60x18** | [0, 2^60) | 1e-18 | Prices, rates, balances |
| **SD59x18** | (-2^59, 2^59) | 1e-18 | Signed: P&L, deltas |
| **UD2x18** | [0, 2^2) | 1e-18 | Small fractions (fees) |
| **SD1x18** | (-2, 2) | 1e-18 | Small signed fractions |
| **UD21x18** | [0, 2^21) | 1e-18 | Medium unsigned |
| **SD21x18** | (-2^21, 2^21) | 1e-18 | Medium signed |

### 2.2 UD60x18 Math Functions

```solidity
// Core arithmetic
avg(x, y)     → (x & y) + ((x ^ y) >> 1)  // SWAR technique
ceil(x)       → smallest whole >= x
div(x, y)     → x * UNIT / y (mulDiv)
exp(x)        → e^x (192-bit precision)
exp2(x)       → 2^x
floor(x)      → largest whole <= x
frac(x)       → fractional part
gm(x, y)      → geometric mean = sqrt(x * y)
inv(x)        → 1/x
ln(x)         → natural log
log10(x)      → base-10 log
log2(x)       → base-2 log
mul(x, y)     → x * y / UNIT
pow(x, y)     → x^y (via exp(y * ln(x)))
powu(x, y)    → x^y (integer exponent, repeated squaring)
sqrt(x)       → Babylonian method
```

### 2.3 Key Implementation Details

**mulDiv (overflow-safe):**
```solidity
function mulDiv(uint256 x, uint256 y, uint256 denominator) → uint256
// Uses 512-bit intermediate via assembly
// Reverts on overflow or denominator = 0
```

**exp() — 192-bit precision:**
```
1. x > MAX_INPUT → revert
2. Decompose: x = k * ln(2) + r, where |r| <= ln(2)/2
3. 2^k via bit shift
4. e^r via Taylor series (192-bit terms)
5. Multiply results
```

**⚠️ Audit notes:**
- All functions use `unchecked` blocks — rely on prior range checks
- `wrap()` function wraps uint256 → UD60x18 WITHOUT validation (unsafe)
- `into()` functions DO validate range
- Rounding: most functions round DOWN. `mulDivUp` rounds UP.
- `pow(x, y)` with y=0 returns UNIT (1.0). `powu(x, 0)` returns UNIT.

### 2.4 When to Use PRB-Math vs Solmate FixedPointMathLib

| | PRB-Math | Solmate |
|---|---------|---------|
| Precision | 18-dec, type-safe | WAD (1e18), raw uint |
| Functions | 20+ (exp, ln, log, pow) | 8 (mulWad, divWad, rpow, sqrt) |
| Gas | Higher (more checks) | Lower (assembly, unchecked) |
| Safety | Type system prevents misuse | Developer must be careful |
| Use case | Complex DeFi math (AMM, lending) | Simple wad math |

---

## 3. BORINGSOLIDITY (BoringCrypto / SushiSwap)

**Filosofi:** Practical, battle-tested, used in production (SushiSwap, Kashi). Not minimal, not maximal.

### 3.1 BoringOwnable

```solidity
contract BoringOwnable is BoringOwnableData {
    address public owner;
    address public pendingOwner;

    function transferOwnership(address newOwner, bool direct, bool renounce) public onlyOwner;
    function claimOwnership() public;  // pendingOwner must call
}
```

**vs OZ:**
- OZ Ownable: direct transfer, `renounceOwnership()` separate
- OZ Ownable2Step: 2-step (propose + accept)
- Boring: COMBINED — `direct=true` = immediate, `direct=false` = 2-step
- Boring: `renounce` flag allows zero address ONLY if explicit

### 3.2 BoringERC20

```solidity
library BoringERC20 {
    function safeSymbol(IERC20 token) → string ("???" fallback)
    function safeName(IERC20 token) → string ("???" fallback)
    function safeDecimals(IERC20 token) → uint8 (18 fallback)
    function safeBalanceOf(IERC20 token, address to) → uint256
    function safeTotalSupply(IERC20 token) → uint256
    function safeTransfer(IERC20 token, address to, uint256 amount)
    function safeTransferFrom(IERC20 token, address from, address to, uint256 amount)
}
```

**vs OZ SafeERC20 / Solmate SafeTransferLib:**
- Boring: high-level `staticcall`/`call` + `abi.decode`
- Solmate: pure assembly (cheapest)
- OZ: assembly + high-level hybrid (most complete)
- Boring unique: `returnDataToString()` handles both string and bytes32 returns

### 3.3 BoringBatchable (⚠️ CRITICAL)

```solidity
contract BaseBoringBatchable {
    function batch(bytes[] calldata calls, bool revertOnFail) external payable {
        for (uint256 i = 0; i < calls.length; i++) {
            (bool success, bytes memory result) = address(this).delegatecall(calls[i]);
            if (!success && revertOnFail) _getRevertMsg(result);
        }
    }
}
```

**⚠️ WARNING (from source):**
```
// WARNING!!!
// Combining BoringBatchable with msg.value can cause double spending issues
// https://www.paradigm.xyz/2021/08/two-rights-might-make-a-wrong/
```

**Attack vector:**
```
batch([
    "deposit{value: 1 ETH}()",   // uses msg.value = 1 ETH
    "deposit{value: 1 ETH}()"    // uses msg.value = 1 ETH AGAIN (same tx)
])
// Total deposited: 2 ETH, but only 1 ETH sent!
```

**Mitigation:** Track `msg.value` usage across batch calls, or don't use `payable` in batchable functions.

### 3.4 BoringRebase

```solidity
library BoringRebase {
    struct Rebase { uint128 elastic; uint128 base; }
    function add(Rebase memory total, uint256 elastic, uint256 base) → (Rebase, uint256, uint256)
    function sub(Rebase memory total, uint256 elastic, uint256 base) → (Rebase, uint256, uint256)
    function toBase(Rebase memory total, uint256 elastic, bool roundUp) → uint256
    function toElastic(Rebase memory total, uint256 base, bool roundUp) → uint256
}
```
→ Used in Kashi lending: elastic = total assets, base = total shares.

### 3.5 Domain (EIP-712)

```solidity
contract Domain {
    bytes32 constant DOMAIN_SEPARATOR = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );
}
```
→ Simplified EIP-712 for permit signatures.

---

## 4. SLITHER 0.11.5 (Trail of Bits / Crytic)

**What:** Static analyzer. Reads Solidity source → finds bugs WITHOUT executing.

### 4.1 Usage

```bash
# Basic scan
slither contracts/

# Specific detectors
slither contracts/ --detect reentrancy-eth,uninitialized-state

# Exclude informational
slither contracts/ --filter-paths "node_modules|test|mock"

# JSON output
slither contracts/ --json output.json

# Specific contract
slither contracts/ --include-contracts "MyContract"

# With foundry
slither . --foundry-compile-all
```

### 4.2 Key Detectors (by severity)

**HIGH:**
| Detector | What it finds |
|----------|---------------|
| `reentrancy-eth` | Reentrancy with ETH transfer |
| `reentrancy-no-eth` | Reentrancy without ETH (state corruption) |
| `uninitialized-state` | State variables never initialized |
| `arbitrary-send-eth` | ETH sent to arbitrary address |
| `controlled-delegatecall` | delegatecall to user-controlled address |
| `suicidal` | Unprotected selfdestruct |
| `unprotected-upgrade` | Unprotected upgrade function |

**MEDIUM:**
| Detector | What it finds |
|----------|---------------|
| `reentrancy-benign` | Reentrancy (no direct loss) |
| `timestamp` | block.timestamp dependency |
| `incorrect-equality` | Dangerous strict equality |
| `unchecked-transfer` | Unchecked transfer return value |
| `shadowing-state` | State variable shadowing |
| `tx-origin-used-for-auth` | tx.origin for authentication |

**LOW/INFO:**
| Detector | What it finds |
|----------|---------------|
| `naming-convention` | Non-standard naming |
| `unused-state` | Unused state variables |
| `costly-loop` | Expensive loop operations |
| `dead-code` | Unreachable code |

### 4.3 Slither for Audit Workflow

```bash
# Step 1: Full scan
slither src/ --json slither_output.json

# Step 2: Filter high/medium
cat slither_output.json | python3 -c "
import json,sys
data = json.load(sys.stdin)
for r in data['results']:
    if r['impact'] in ['High','Medium']:
        print(f\"[{r['impact']}] {r['check']}: {r['description'][:100]}\")
"

# Step 3: Check specific patterns
slither src/ --detect reentrancy-eth,reentrancy-no-eth
slither src/ --detect uninitialized-state,unprotected-upgrade
slither src/ --detect arbitrary-send-eth,controlled-delegatecall
```

### 4.4 Slither Limitations

- ❌ Can't find logic bugs (only pattern-based)
- ❌ False positives on complex inheritance
- ❌ Doesn't understand cross-contract invariants
- ❌ Can't detect oracle manipulation
- ✅ Best for: reentrancy, access control, uninitialized vars
- ✅ Fast: scans entire codebase in seconds

---

## 5. MYTHRIL v0.24.8 (ConsenSys)

**What:** Symbolic execution engine. Explores ALL possible execution paths.

### 5.1 Usage

```bash
# Analyze single file
python3 -m mythril analyze src/MyContract.sol

# Analyze deployed contract
python3 -m mythril analyze -a 0x... --rpc-url https://mainnet.base.org

# With solc version
python3 -m mythril analyze src/MyContract.sol --solv 0.8.20

# Specific function
python3 -m mythril analyze src/MyContract.sol -f "withdraw()"

# Timeout (default 5 min)
python3 -m mythril analyze src/MyContract.sol --execution-timeout 120

# Max depth
python3 -m mythril analyze src/MyContract.sol --max-depth 10
```

### 5.2 What Mythril Finds

| Bug Type | Detection Method |
|----------|-----------------|
| **Integer overflow/underflow** | Symbolic math exploration |
| **Reentrancy** | State exploration across calls |
| **Unchecked return values** | Path analysis |
| **Access control bypass** | Constraint solving on msg.sender |
| **Assert violations** | Reachability analysis |
| **Ether lock** | No withdrawal path exists |
| **Delegatecall to arbitrary** | Symbolic address resolution |

### 5.3 Mythril vs Slither

| | Slither | Mythril |
|---|---------|---------|
| Method | Static analysis (pattern) | Symbolic execution (explore paths) |
| Speed | Seconds | Minutes-hours |
| Depth | Surface patterns | Deep logic exploration |
| False positives | Medium | Low (proves exploit exists) |
| False negatives | High (misses logic bugs) | Medium (bounded by timeout) |
| Best for | Quick first pass | Deep dive on specific functions |
| Input | Source code | Source OR bytecode |

### 5.4 Mythril Audit Workflow

```bash
# Step 1: Slither first (fast, broad)
slither src/ --json slither.json

# Step 2: Mythril on HIGH findings
python3 -m mythril analyze src/Vault.sol --execution-timeout 300

# Step 3: Mythril on deployed bytecode (no source needed)
python3 -m mythril analyze -a 0xTARGET --rpc-url $RPC

# Step 4: Focus on specific functions
python3 -m mythril analyze src/Vault.sol -f "withdraw(uint256)"
python3 -m mythril analyze src/Vault.sol -f "deposit(uint256)"
```

### 5.5 Mythril Limitations

- ❌ SLOW (minutes per function)
- ❌ Path explosion on complex contracts
- ❌ Can't handle external calls well (assumes worst case)
- ❌ Doesn't understand AMM math / oracle patterns
- ✅ Best for: access control, integer bugs, reentrancy proofs
- ✅ Can analyze DEPLOYED bytecode (no source needed!)

---

## 6. ECHIDNA 2.2.6 (Trail of Bits)

**What:** Property-based fuzzer. Generates random inputs → checks invariants.

### 6.1 Setup

```yaml
# echidna_config.yaml
testMode: assertion        # or: property, optimization, exploration
testLimit: 50000           # number of test cases
shrinkLimit: 5000          # shrinking iterations
coverage: true             # track code coverage
corpusDir: corpus          # save test cases
seqLen: 100                # max calls per sequence
deployer: "0x10000"        # deployer address
sender: ["0x10000", "0x20000", "0x30000"]  # msg.sender values
```

### 6.2 Writing Properties

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "../src/Vault.sol";

contract VaultFuzz is Test {
    Vault vault;
    address attacker = address(0xDEAD);

    function setUp() public {
        vault = new Vault();
        // Fund vault
        vm.deal(address(vault), 100 ether);
    }

    // PROPERTY: total deposits must equal vault balance
    function echidna_invariant_solvency() public view returns (bool) {
        return address(vault).balance >= vault.totalDeposits();
    }

    // PROPERTY: user can't withdraw more than deposited
    function echidna_no_overdraft() public view returns (bool) {
        return vault.balanceOf(attacker) <= vault.totalDeposits();
    }

    // PROPERTY: owner never changes unexpectedly
    function echidna_owner_stable() public view returns (bool) {
        return vault.owner() == address(this);
    }

    // ASSERTION MODE: test specific scenarios
    function test_fuzz_withdraw(uint256 amount) public {
        vm.assume(amount > 0 && amount <= 100 ether);
        vm.prank(attacker);
        vault.deposit{value: amount}();
        vm.prank(attacker);
        vault.withdraw(amount);
        assert(vault.balanceOf(attacker) == 0);
    }
}
```

### 6.3 Usage

```bash
# Basic fuzz
echidna src/Vault.sol --contract VaultFuzz --config echidna_config.yaml

# Assertion mode
echidna src/Vault.sol --contract VaultFuzz --test-mode assertion

# Property mode (echidna_ prefix functions)
echidna src/Vault.sol --contract VaultFuzz --test-mode property

# With coverage
echidna src/Vault.sol --contract VaultFuzz --coverage --corpus-dir corpus

# Multi-ABI (for complex contracts)
echidna src/Vault.sol --contract VaultFuzz --abi-dir abis/
```

### 6.4 Echidna Test Modes

| Mode | Function Prefix | What it does |
|------|----------------|--------------|
| **property** | `echidna_*` | Check invariant returns true |
| **assertion** | `test_*` / `assert` | Check no assertion fails |
| **optimization** | `echidna_*` | Maximize return value |
| **exploration** | any | Maximize code coverage |

### 6.5 Echidna vs Foundry Fuzz

| | Echidna | Foundry `forge test --fuzz` |
|---|---------|---------------------------|
| Sequences | Multi-call (up to seqLen) | Single call per test |
| Shrinking | Advanced (finds minimal repro) | Basic |
| Coverage | Built-in, detailed | Basic |
| Corpus | Saves failing cases | No |
| Invariants | `echidna_*` pattern | `invariant_*` pattern |
| Speed | Slower (more thorough) | Faster |
| Best for | Deep invariant testing | Quick property checks |

### 6.6 Echidna Audit Workflow

```bash
# Step 1: Write invariants based on protocol docs
# - Solvency: assets >= liabilities
# - Access: only owner can admin
# - Conservation: mint + transfer = totalSupply
# - Monotonic: balances only change via deposit/withdraw

# Step 2: Run with high test limit
echidna src/ --contract Fuzz --test-limit 100000 --seq-len 200

# Step 3: Check coverage
echidna src/ --contract Fuzz --coverage --corpus-dir corpus
# Open corpus/coverage.html

# Step 4: If found violation → shrink → minimal repro
# Echidna auto-shrinks to minimal call sequence

# Step 5: Add failing case to Foundry test suite for regression
```

---

## 7. COMPARISON MATRIX

### Libraries

| | Solmate | OZ | PRB-Math | BoringSolidity |
|---|---------|-----|---------|----------------|
| **Gas** | ⭐⭐⭐ Lowest | ⭐⭐ Medium | ⭐⭐ Medium | ⭐⭐ Medium |
| **Safety** | ⭐ Minimal checks | ⭐⭐⭐ Full checks | ⭐⭐⭐ Type-safe | ⭐⭐ Practical |
| **Completeness** | ⭐⭐ Core only | ⭐⭐⭐ Everything | ⭐ Math only | ⭐⭐ DeFi focused |
| **Audit-friendly** | ⭐⭐ Assembly heavy | ⭐⭐⭐ Well-documented | ⭐⭐⭐ Formal proofs | ⭐⭐ Battle-tested |
| **Used by** | Uniswap V4, Blur | Aave, Compound | PRBProxy, Sablier | SushiSwap, Kashi |

### Security Tools

| | Slither | Mythril | Echidna |
|---|---------|---------|---------|
| **Method** | Static analysis | Symbolic execution | Fuzzing |
| **Speed** | ⭐⭐⭐ Seconds | ⭐ Minutes | ⭐⭐ Minutes |
| **Depth** | ⭐ Patterns | ⭐⭐⭐ Path exploration | ⭐⭐⭐ Invariant breaking |
| **False positives** | ⭐⭐ Medium | ⭐ Low | ⭐ Very low |
| **Setup** | ⭐⭐⭐ Zero config | ⭐⭐ Some config | ⭐⭐ Write properties |
| **Best for** | First pass, CI/CD | Deep dive, bytecode | Invariant testing |

### Recommended Audit Pipeline

```
1. slither src/                          → broad scan (seconds)
2. python3 -m mythril analyze src/X.sol  → deep dive on critical functions (minutes)
3. echidna src/ --contract Fuzz          → invariant fuzzing (minutes-hours)
4. forge test --fuzz                     → regression tests
5. Manual review                         → logic, economics, oracle
```

---

## 8. QUICK REFERENCE — COMMANDS

```bash
# Slither
slither . --json report.json
slither . --detect reentrancy-eth,unprotected-upgrade
slither . --filter-paths "test|mock|lib"

# Mythril
python3 -m mythril analyze src/Vault.sol --execution-timeout 300
python3 -m mythril analyze -a 0xTARGET --rpc-url $RPC

# Echidna
echidna src/ --contract Fuzz --test-mode property --test-limit 50000
echidna src/ --contract Fuzz --test-mode assertion --coverage

# Foundry (complement)
forge test --fuzz-runs 10000
forge test --match-contract "Invariant" -vvv
```

---

*Dibaca dari source. Tested on this machine.*
*Solmate v6.8.0 · PRB-Math v4.1.2 · BoringSolidity latest*
*Slither 0.11.5 · Mythril v0.24.8 · Echidna 2.2.6 · Halmos 0.3.3*
*BOZAGENTIC · "Scan fast. Fuzz deep. Prove it breaks."*

---

## 9. HALMOS 0.3.3 (a16z)

**What:** Symbolic testing framework. Runs Foundry tests with SYMBOLIC inputs (not random). Proves properties hold for ALL possible inputs.

**Installed:** `pip install halmos` → halmos 0.3.3 + Z3 4.12.6 + Yices 2.6.4

### 9.1 How It Works

```
Foundry fuzz:  "try 256 random values → probably fine"
Halmos:        "prove for ALL uint256 values → mathematically certain"

Halmos converts your test into SMT constraints → Z3/Yices solver proves
whether ANY input can violate your assertion.
```

### 9.2 Usage

```bash
# Run all symbolic tests (check_* and invariant_* prefix)
halmos --contract MyTest

# Specific solver
halmos --contract MyTest --solver z3
halmos --contract MyTest --solver yices

# With timeout per assertion (ms)
halmos --contract MyTest --solver-timeout-assertion 10000

# Verbose (show paths explored)
halmos --contract MyTest -v

# JSON output
halmos --contract MyTest --json-output results.json

# Loop unrolling bound
halmos --contract MyTest --loop 5

# Invariant depth (stateful sequences)
halmos --contract MyTest --invariant-depth 3
```

### 9.3 Writing Symbolic Tests

```solidity
contract MySymbolicTest is Test {
    // Prefix: check_ (property) or invariant_ (stateful)

    // SYMBOLIC: for ALL uint256 inputs, property holds
    function check_property(uint256 x, uint256 y) public {
        vm.assume(y != 0);  // constraint
        assert(x / y <= x);  // PROVEN for all x, y
    }

    // SYMBOLIC: access control
    function check_only_owner(address caller) public {
        vm.assume(caller != owner);
        vm.prank(caller);
        contract.adminFunction();
        // If ALL paths revert → access control proven
        // Halmos reports "all paths reverted" = PROVEN SAFE
    }

    // STATEFUL INVARIANT: holds across sequences of calls
    function invariant_solvency() public view {
        assert(vault.totalAssets() >= vault.totalShares());
    }
}
```

### 9.4 Halmos vs Other Tools

| | Halmos | Echidna | Mythril | Foundry Fuzz |
|---|--------|---------|---------|--------------|
| Method | Symbolic (SMT) | Random fuzz | Symbolic exec | Random fuzz |
| Guarantee | **PROOF** (all inputs) | Probabilistic | Path-bounded | Probabilistic |
| Inputs | Symbolic (all values) | Random concrete | Symbolic | Random concrete |
| Counterexample | Minimal (from solver) | Shrunk | From path | Random |
| Speed | Fast (per-property) | Slow (many runs) | Slow | Fast |
| Setup | Foundry-compatible | Separate config | Separate | Built-in |
| Cheatcodes | Partial (no expectRevert) | N/A | N/A | Full |
| Best for | Proving invariants | Breaking invariants | Deep path exploration | Quick checks |

### 9.5 Key Differences from Foundry Fuzz

```
Foundry:  test_fuzz(uint256 x) → runs 256 random x values
Halmos:   check_prop(uint256 x) → proves for ALL 2^256 possible x values

Foundry:  "I tried 256 values, none broke it"
Halmos:   "I PROVED no value can break it" (or finds exact counterexample)
```

### 9.6 Supported Cheatcodes

| Cheatcode | Status |
|-----------|--------|
| `vm.prank()` | ✅ |
| `vm.assume()` | ✅ |
| `vm.deal()` | ✅ |
| `vm.warp()` | ✅ |
| `vm.roll()` | ✅ |
| `vm.expectRevert()` | ❌ NOT SUPPORTED |
| `vm.expectEmit()` | ❌ NOT SUPPORTED |
| `vm.mockCall()` | ❌ NOT SUPPORTED |

**Workaround for expectRevert:**
```solidity
// DON'T:
vm.expectRevert();
contract.fn();

// DO:
contract.fn();
assert(false);  // if all paths revert → property proven
// Halmos reports "all paths reverted" = SAFE
```

### 9.7 Halmos Config (halmos.toml)

```toml
[default]
solver = "z3"
solver-timeout-assertion = 10000
loop = 3
invariant-depth = 2
verbosity = 1
```

### 9.8 Audit Workflow with Halmos

```bash
# Step 1: Write properties from protocol invariants
# - Solvency: assets >= liabilities
# - Access control: only authorized callers
# - Conservation: no tokens created/destroyed unexpectedly
# - Monotonicity: values only change in expected direction

# Step 2: Run symbolic tests
halmos --contract ProtocolTest --solver z3

# Step 3: If PASS → property PROVEN for all inputs
# If FAIL → counterexample provided (exact input that breaks it)

# Step 4: Combine with Echidna for stateful sequences
echidna src/ --contract Fuzz --test-mode property

# Step 5: Slither + Mythril for pattern-based + path exploration
```

### 9.9 Verified Output (DrainerEvolusi)

```
Running 4 tests for HalmosDrainerTest
[PASS] check_drain_bounded(uint256,uint256)     (paths: 9, time: 0.25s)
[PASS] check_supply_conservation(uint256)       (paths: 4, time: 0.06s)
[PASS] check_zero_allowance(uint256)            (paths: 2, time: 0.05s)
[PROVEN] check_access_control(address,address)  (all paths reverted = SAFE)
```

→ Drain NEVER exceeds allowance. PROVEN for all 2^256 × 2^256 input combinations.
→ Non-owner NEVER drains. PROVEN for all 2^160 possible caller addresses.

### 9.10 When to Use Halmos

| Use Halmos when | Use Echidna when |
|-----------------|------------------|
| Proving mathematical invariants | Breaking complex stateful systems |
| Access control verification | Multi-call sequence attacks |
| Arithmetic properties (overflow, bounds) | Cross-contract interactions |
| Simple, fast proofs | Deep exploration with coverage |
| CI/CD (fast, deterministic) | Pre-audit deep dive |

**Best combo:** Halmos (prove properties) + Echidna (try to break them) + Slither (patterns) + Mythril (paths)
