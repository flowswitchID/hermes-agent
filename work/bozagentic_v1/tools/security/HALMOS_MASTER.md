# HALMOS MASTER — Symbolic Execution Reference
# BOZAGENTIC | Properties, patterns, limitations

---

## BASICS

```bash
# Run all properties in a contract
halmos --contract MyContract

# Run specific function
halmos --contract MyContract --function check_foo

# With timeout and statistics
halmos --contract MyContract --solver-timeout-assertion 10000 --statistics

# Verbose output
halmos --contract MyContract -v
```

## PROPERTY NAMING

```solidity
// Halmos recognizes these prefixes:
function check_foo() ...    // property (assert-based)
function invariant_foo() ... // invariant (stateful)
function prove_foo() ...    // property (alternative prefix)
```

## KEY PATTERNS

### 1. Simple assertion
```solidity
function check_addition(uint256 a, uint256 b) external pure {
    if (a + b < a) return; // skip overflow
    assert(a + b >= a);
}
```

### 2. Stateful property (deploy + interact)
```solidity
contract MyProps {
    MyContract target;
    constructor() { target = new MyContract(); }
    
    function check_state(uint256 x) external {
        target.doSomething(x);
        assert(target.value() <= MAX);
    }
}
```

### 3. Bug existence proof
```solidity
function check_bug_exists(uint120 a, uint120 b, uint120 cap) external pure {
    if (a == 0 || b == 0 || cap == 0) return;
    bool passA = a <= cap;
    bool passB = b <= cap; // BUG: ignores a
    if (passA && passB) {
        // assert(a + b <= cap); // WOULD FAIL (proves bug)
        // Instead: verify correct impl catches it
        bool correctPassB = (uint256(a) + b) <= cap;
        if (!correctPassB) {
            assert(uint256(a) + b > cap); // bug confirmed
        }
    }
}
```

### 4. Fix verification
```solidity
function check_fix_works(uint120 a, uint120 b, uint120 cap) external pure {
    if (a == 0 || b == 0 || cap == 0) return;
    bool passA = a <= cap;
    bool passB = (uint256(a) + b) <= cap; // CORRECT: counts a
    if (passA && passB) {
        assert(uint256(a) + b <= cap); // ALWAYS holds
    }
}
```

---

## LINEAR vs NONLINEAR

```
LINEAR (fast, < 1s):
  ✅ Addition, subtraction
  ✅ Comparison (<=, >=, ==, !=)
  ✅ Bitwise AND/OR/XOR
  ✅ Shift (<<, >>)
  ✅ Type casting (uint120 → uint256)

NONLINEAR (slow, often timeout):
  ❌ Multiplication of large bitvectors
  ❌ Division (especially by non-power-of-2)
  ❌ Modulo
  ❌ payment * bps / 10000 pattern

WORKAROUNDS for nonlinear:
  1. Use Z3 directly with Int (not BitVec)
  2. Bound inputs to small ranges
  3. Increase --solver-timeout-assertion
  4. Split into linear sub-properties
  5. Use Foundry fuzz for nonlinear (10K+ runs)
```

---

## PROJECT SETUP

```bash
# IMPORTANT: Use minimal project to avoid compile timeout
mkdir halmos-test && cd halmos-test
forge init --no-commit .

# Write properties in test/
# Run:
halmos --contract MyProps --solver-timeout-assertion 10000
```

### Common mistake:
```
❌ Running halmos in large project (Flywheel, Commerce)
   → Compiles ALL contracts → timeout before tests run

✅ Extract logic to minimal project
   → Compiles in < 1s → tests run instantly
```

---

## RESULTS FROM COINBASE AUDIT

```
PROPERTY                          | RESULT  | TIME
══════════════════════════════════|═════════|══════
check_bypass_bug                  | PASS ✅ | 0.13s
check_correct_impl                | PASS ✅ | 0.08s
check_no_overflow                 | PASS ✅ | 0.46s
check_zero_bps                    | PASS ✅ | 0.01s
check_cap_bounded (uint128)       | TIMEOUT | 10s
check_full_bps (uint128)          | TIMEOUT | 10s
check_monotonic (uint128)         | TIMEOUT | 10s
check_ownerCount_positive         | PASS ✅ | 0.01s
check_isOwner                     | PASS ✅ | 0.02s
check_noZeroOwner                 | FAIL ❌ | 0.15s (found bug!)
check_deposit_increases           | PASS ✅ | 0.13s
check_withdraw_decreases          | PASS ✅ | 0.14s
check_total_ge_individual         | PASS ✅ | 0.02s
check_no_overdraft                | PASS ✅ | 0.03s
check_period_deterministic        | PASS ✅ | 0.05s
check_period_monotonic            | FAIL ❌ | 3.4s (uint32 overflow)
check_spend_bounded               | PASS ✅ | 0.40s
check_period_reset                | PASS ✅ | 0.12s
check_cei_order                   | PASS ✅ | 0.07s
```

---

## LEVEL ASSESSMENT

```
BEFORE: 50% (2 runs, mostly confused)
NOW:    75% (19 properties, bug found, limitations understood)
EXPERT: 90% (ghost vars, hooks, multi-contract, quantifiers)
GAP:    ghost variables, hooks, forall/exists quantifiers
```
