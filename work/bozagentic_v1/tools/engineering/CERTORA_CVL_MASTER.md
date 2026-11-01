# CERTORA PROVER + CVL — STUDY NOTES
# Formal Verification for Smart Contracts
# BOZAGENTIC · 2026-07-30

---

## 1. WHAT IS CERTORA

```
Type:     Formal verification (mathematical proof)
Model:    Cloud-based (needs API key)
CLI:      certora-cli (pip install certora-cli)
Language: CVL (Certora Verification Language)
What:     Proves properties hold for ALL possible inputs/states
          Not testing (samples) — PROVING (exhaustive)
Cost:     Free tier available, paid for heavy usage
```

### vs Echidna/Scribble:
```
Echidna:   Fuzzing (random inputs, finds counterexamples)
Scribble:  Runtime verification (checks properties during execution)
Certora:   Formal proof (mathematically proves for ALL inputs)

Echidna:   "I tried 100K random inputs, no bug found"
Certora:   "I PROVED no input can violate this property"

Certora is STRONGER but SLOWER and harder to write.
Best practice: Echidna first (fast), Certora for critical invariants.
```

---

## 2. CVL SYNTAX (from our MiniVault.spec)

### Methods block:
```cvl
methods {
    function totalAssets() external returns (uint256) envfree;
    function shares(address) external returns (uint256) envfree;
}
// envfree = can be called without transaction context (view functions)
```

### Ghost variables:
```cvl
ghost uint256 ghostTotalDeposited {
    init_state axiom ghostTotalDeposited == 0;
}

ghost mapping(address => uint256) ghostUserDeposits {
    init_state axiom forall address a. ghostUserDeposits[a] == 0;
}
// Ghost = exists only in spec, not in contract
// Tracks state that Solidity can't express
```

### Invariants (hold in EVERY reachable state):
```cvl
invariant solvency()
    totalShares() == 0 || totalAssets() >= totalShares();

invariant feeCap()
    feeBps() <= 1000;

invariant shareConservation()
    forall address a. shares(a) <= totalShares();
```

### Rules (properties across transactions):
```cvl
rule depositIncreasesAssets(method f, env e, calldataarg args) {
    uint256 before = totalAssets();
    f(e, args);
    uint256 after = totalAssets();
    assert (f.selector == sig:deposit(uint256).selector) =>
        after > before;
}
```

### Quantified properties:
```cvl
rule noShareOverflow(env e, address user) {
    assert shares(user) <= totalShares();
    // Certora checks this for ALL possible addresses
}
```

### Key CVL keywords:
```
envfree        — function callable without tx context
env            — transaction environment (msg.sender, value, etc.)
calldataarg    — arbitrary function arguments
method         — arbitrary function (for parametric rules)
forall         — universal quantifier (for all)
exists         — existential quantifier (there exists)
axiom          — assumption (taken as true)
assert         — property to prove
require        — precondition (assumed true)
sig:           — function selector
init_state     — initial state constraint
preserved      — induction step (if true before, true after)
```

---

## 3. HOW TO RUN

```bash
# Install
pip install certora-cli

# Get API key from https://prover.certora.com/
export CERTORA_KEY=<your-key>

# Run with .conf file
certoraRun certora.conf

# certora.conf format:
{
  "files": ["src/Contract.sol"],
  "verify": "ContractName:specs/Spec.spec",
  "solc": "solc0.8.27",
  "optimistic_loop": true,
  "loop_iter": 3
}

# Or CLI directly:
certoraRun src/Contract.sol \
  --verify ContractName:specs/Spec.spec \
  --solc solc0.8.27
```

---

## 4. WHAT WE WROTE (MiniVault.spec)

```
5 invariants:
  1. solvency — totalAssets >= totalShares
  2. feeCap — feeBps <= 1000
  3. shareConservation — forall user: shares <= totalShares
  4. ownerOnlyFee — only owner changes fee
  5. pauseBlocksDeposit — paused blocks deposits

5 rules:
  1. depositIncreasesAssets — deposit always increases totalAssets
  2. withdrawBoundedByShare — withdraw never exceeds proportional share
  3. sharePriceNonDecreasing — share price monotonically non-decreasing
  4. feeChangeRequiresOwner — non-owner fee change reverts
  5. pauseBlocksDeposit — deposit reverts when paused

2 quantified properties:
  1. noShareOverflow — forall user: shares <= total
  2. depositProportional — minted shares exactly proportional

3 ghost variables:
  1. ghostTotalDeposited — cumulative deposits
  2. ghostTotalWithdrawn — cumulative withdrawals
  3. ghostUserDeposits — per-user cumulative deposits
```

---

## 5. LIMITATIONS

```
❌ Cannot run without API key (cloud-based)
❌ Slow (minutes to hours per proof)
❌ CVL has learning curve (different from Solidity)
❌ Cannot verify external calls / cross-contract easily
❌ Loop handling requires manual bounds (loop_iter)
❌ Not all Solidity features supported (assembly, etc.)

✅ Strongest guarantee (mathematical proof)
✅ Parametric rules (check ALL functions at once)
✅ Quantifiers (forall/exists over addresses)
✅ Ghost variables for history tracking
✅ Industry standard for formal verification
```

---

## 6. WHEN TO USE CERTORA vs ECHIDNA

```
USE ECHIDNA WHEN:
  → Quick feedback (seconds to minutes)
  → Finding bugs (counterexamples)
  → Complex multi-contract systems
  → During development (fast iteration)

USE CERTORA WHEN:
  → Critical invariants (solvency, conservation)
  → Need mathematical proof (not just testing)
  → Protocol handles >$100M TVL
  → Pre-launch final verification
  → Compliance / institutional requirements

BEST PRACTICE (CD-style):
  1. Write Scribble annotations (fast, in-code)
  2. Fuzz with Echidna (find counterexamples)
  3. Fix bugs found by Echidna
  4. Write CVL for critical invariants (prove)
  5. Run Certora as final gate before deployment
```

---

*BOZAGENTIC · Certora CVL Study Complete*
*CLI installed, spec written, syntax documented*
*Needs API key to execute proofs*
