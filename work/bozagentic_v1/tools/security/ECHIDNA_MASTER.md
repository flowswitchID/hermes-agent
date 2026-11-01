# ECHIDNA MASTER — Property-Based Fuzzing Reference
# BOZAGENTIC | Corpus, shrink, targeted invariants

---

## BASICS

```bash
# Run with config
echidna test/MyTest.t.sol --contract MyContract --config config.yaml

# Config file (config.yaml):
testMode: property        # or assertion
testLimit: 50000          # number of test sequences
shrinkLimit: 5000         # shrinking iterations on failure
corpusDir: "corpus"       # save/load corpus
coverage: true            # track code coverage
deployer: "0x10000"       # deployer address
sender: ["0x10000"]       # sender addresses
maxTimeDelay: 604800      # max block.timestamp advance
maxBlockDelay: 60480      # max block.number advance
```

## TEST MODES

```
property:    Functions prefixed with echidna_ returning bool
assertion:   Any assert() failure = bug
optimization: Maximize a value (find worst case)
exploration:  Maximize coverage (no pass/fail)
```

## PROPERTY PATTERNS

### 1. Simple invariant
```solidity
function echidna_total_supply() external view returns (bool) {
    return token.totalSupply() <= MAX_SUPPLY;
}
```

### 2. Stateful (interact then check)
```solidity
function deposit(uint256 amount) external {
    amount = bound(amount, 1, 1e18);
    vault.deposit(amount);
}

function echidna_solvency() external view returns (bool) {
    return vault.totalAssets() >= vault.totalSupply();
}
```

### 3. Targeted bug detection (CashbackRewards pattern)
```solidity
function allocateThenSend(uint120 a, uint120 s) external {
    // Simulate the buggy operations
    allocate(a);
    send(s);
}

function echidna_cap_invariant() external view returns (bool) {
    return allocated + distributed <= cap;
}
// This FAILS → proves bug exists
```

### 4. Differential testing
```solidity
function echidna_safe_equals_naive(uint256 amount, uint256 bps) external pure returns (bool) {
    amount = bound(amount, 0, type(uint128).max);
    bps = bound(bps, 0, 10000);
    return safePercent(amount, bps) == naivePercent(amount, bps);
}
```

---

## ADVANCED FEATURES

### Corpus replay
```bash
# Save corpus from previous run
echidna test.t.sol --corpus-dir my-corpus ...

# Replay corpus (deterministic)
echidna test.t.sol --corpus-dir my-corpus --test-limit 10000 ...

# Corpus contains:
#   reproducers/  — failing sequences
#   coverage/     — coverage data (lcov, html)
#   cache/        — internal state
```

### Shrinking
```bash
# When a bug is found, Echidna shrinks the input
# shrinkLimit: 5000 (default)
# Lower = faster but less minimal
# Higher = more minimal but slower
```

### Multi-sender
```yaml
sender: ["0x10000", "0x20000", "0x30000"]
# Tests interactions between different addresses
```

### Coverage-guided
```yaml
coverageEnabled: true
# Echidna prioritizes inputs that reach new code
# Check: corpus/coverage/covered.html
```

---

## RESULTS FROM COINBASE AUDIT

```
TEST                           | RUNS   | RESULT
═══════════════════════════════|════════|══════════
CashbackInvariantModel         | 50K    | FOUND BUG 💥
  allocate(4568) + sendBuggy(433) = 5001 > 5000
CashbackFullHarness            | 50K    | PASS ✅
BuilderCodesEchidna            | 100K   | PASS ✅
SpendPermissionEchidna         | 50K    | PASS ✅
ToTokenIdFuzz (Foundry)        | 10K    | PASS ✅
DifferentialSafePercent        | 10K    | PASS ✅
```

---

## LEVEL ASSESSMENT

```
BEFORE: 70% (basic setup, simple invariants)
NOW:    82% (targeted invariants, corpus, shrink, differential)
EXPERT: 92% (custom mutators, grammar-based, multi-contract)
GAP:    custom mutators, grammar-based fuzzing
```
