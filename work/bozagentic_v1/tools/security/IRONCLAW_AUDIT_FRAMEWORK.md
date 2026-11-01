# BOZAGENTIC UNIFIED AUDIT FRAMEWORK
# Gabungan 7 firm methodologies → 1 proses
# Setiap audit WAJIB follow ini. No exceptions.
# BOZAGENTIC · 2026-07-30

---

## STEP 1: RECON (Halborn-style Attack Surface Mapping)
## Waktu: 1-2 jam
## Goal: Gambar SELURUH attack surface sebelum baca code

```
1.1 — Protocol Intelligence
    □ Baca docs/whitepaper/README
    □ Gambar flow diagram (duit masuk → proses → keluar)
    □ Identifikasi semua actors: user, admin, keeper, oracle, liquidator
    □ Identifikasi semua trust assumptions
    □ Cek: udah diaudit sebelumnya? Report publik?

1.2 — Contract Inventory
    □ List SEMUA contracts in scope
    □ Untuk setiap contract: size, inheritance, external calls
    □ Gambar dependency graph (A calls B calls C)
    □ Identifikasi external dependencies (oracle, DEX, bridge, token)

1.3 — Entry Point Mapping (Halborn)
    □ List SEMUA external/public functions
    □ Classify: user-facing / admin / keeper / callback / view
    □ Untuk setiap entry: siapa bisa call? apa efeknya?
    □ Identifikasi NON-CONTRACT entry points:
      → Frontend (kalau ada)
      → API/backend (kalau ada)
      → Deploy scripts
      → Admin key management

1.4 — Invariant Definition (Cyfrin-style)
    Tulis invariants SEBELUM baca logic:
    
    SOLVENCY:
      - totalAssets >= totalShares (vault)
      - totalCollateral >= totalDebt (lending)
      - reserve balance >= outstanding claims
      
    ACCESS:
      - Admin functions require authorization
      - User can't access other user's funds
      - No function callable before initialization
      
    CONSERVATION:
      - sum(balances) == totalSupply
      - Tokens in == tokens out + fees
      - No value created from nothing
      
    MONOTONIC:
      - Interest rate >= 0
      - Share price never decreases (without withdrawal)
      - Debt never decreases (without repayment)
```

---

## STEP 2: AUTOMATED SCAN (ToB-style Tooling)
## Waktu: 30 min - 1 jam
## Goal: Triage hot spots, BUKAN final findings

```
2.1 — Slither (Static Analysis)
    slither . --print human-summary
    slither . --detect reentrancy-eth,reentrancy-no-eth
    slither . --detect arbitrary-send,unprotected-upgrade
    slither . --detect unchecked-transfer,unchecked-lowlevel
    slither . --detect uninitialized-state,uninitialized-local
    slither . --detect unused-return,missing-zero-check
    slither . --print data-dependency
    slither . --print inheritance-graph
    
    → Catat semua findings
    → Classify: TRUE POSITIVE / FALSE POSITIVE / NEEDS MANUAL
    → JANGAN langsung report — verify manual dulu

2.2 — Echidna (Property Fuzzing)
    Tulis properties dari Step 1.4:
    
    contract Invariants {
        function echidna_solvency() public returns (bool) {
            return vault.totalAssets() >= vault.totalSupply();
        }
        function echidna_access() public returns (bool) {
            // admin function reverted for non-admin
        }
        function echidna_conservation() public returns (bool) {
            return sum_balances == totalSupply;
        }
    }
    
    echidna Invariants.sol --test-mode assertion --test-limit 100000
    
    → Kalau Echidna nemu counterexample → BUG CONFIRMED
    → Simpan sequence sebagai PoC

2.3 — Halmos (Symbolic Proof)
    // Prove access control
    function prove_onlyOwner() public {
        vm.assume(msg.sender != owner);
        vm.expectRevert();
        contract.adminFunction();
    }
    
    halmos --contract MyTest
    
    → "All paths reverted" = PROVEN SAFE
    → Counterexample = BUG

2.4 — Foundry Fuzz (Cyfrin-style)
    function testFuzz_DepositWithdraw(uint256 amount) public {
        vm.assume(amount > 0 && amount < type(uint128).max);
        deposit(amount);
        uint256 withdrawn = withdraw(amount);
        assertEq(withdrawn, amount); // conservation
    }
    
    forge test --fuzz-runs 100000
    
    → Invariant breaks = investigate root cause
```

---

## STEP 3: MANUAL REVIEW — MULTI-PASS (Spearbit-style Collision)
## Waktu: days
## Goal: Deep understanding, find what tools miss

### PASS A: Architecture & Trust (independent)
```
Baca dari ATAS:

□ Constructor/Initializer
  → State setup correct?
  → _disableInitializers() present?
  → Owner/admin set correctly?
  → Storage layout safe (upgradeable)?

□ Inheritance chain
  → Diamond problem?
  → Function override conflicts?
  → Storage collision risk?

□ Access control model
  → Draw permission matrix:
    Function | Owner | Admin | Keeper | User | Anyone
  → Every cell: correct?
  → Missing restrictions?

□ Trust boundaries
  → Where does trust transfer?
  → External calls = trust boundary
  → Callbacks = trust boundary
  → Oracle data = trust boundary
```

### PASS B: Function-by-Function (independent)
```
Untuk SETIAP external function, jawab 25 pertanyaan:

ACCESS:
  1. Siapa yang bisa call?
  2. Ada modifier protection?
  3. Bisa di-call via delegatecall?
  4. Bisa di-call dari contract (bukan EOA)?
  5. Ada reentrancy guard?

INPUT:
  6. amount = 0 → apa yang terjadi?
  7. amount = max uint → overflow?
  8. address = address(0) → burn/stuck?
  9. array length mismatch → revert?
  10. bytes = empty → handled?

STATE:
  11. State update BEFORE external call? (CEI)
  12. Bisa di-call 2x dalam 1 tx?
  13. State transition valid?
  14. Ada race condition?
  15. Lazy update → stale state exploitable?

EXTERNAL:
  16. Return value checked?
  17. Target bisa revert → DoS?
  18. Target bisa re-enter?
  19. Target bisa be malicious contract?
  20. Gas forwarded correctly?

MATH:
  21. Rounding favors protocol or user?
  22. Division before multiplication?
  23. Precision loss in conversion?
  24. Fixed-point decimals consistent?
  25. mulDiv vs sequential mul/div?
```

### PASS C: Cross-Function & Economic (Sherlock-style)
```
□ Flash loan attack simulation:
  "Kalau gue flash loan X, call A, call B, repay..."
  → Profitable? → CRITICAL

□ Multi-tx attack:
  "Tx1: setup position. Tx2: exploit."
  → Possible? → HIGH

□ Economic modeling (Sherlock):
  "TVL = $10M. Attacker capital = $100K."
  "Can attacker extract > $100K?"
  → Yes → profitable → finding

□ Governance attack:
  "Flash loan voting tokens → propose → vote → execute"
  → votingDelay = 0? → CRITICAL
  → proposalThreshold = 0? → HIGH

□ Oracle manipulation:
  "Flash loan → swap → manipulate price → exploit → repay"
  → TWAP or spot? → Spot = vulnerable

□ Liquidation spiral:
  "Price drops 50% → mass liquidation → price drops more"
  → Incentives aligned? → Dutch auction? → Backstop?
```

### PASS D: External Dependencies (Quantstamp-style)
```
□ Oracle:
  → Source? Chainlink/Uniswap/Custom?
  → Staleness check? Heartbeat?
  → Manipulable in 1 tx?
  → Fallback if oracle down?

□ Token:
  → Standard ERC20? Quirks?
  → Fee-on-transfer? (USDT, PAXG)
  → Rebasing? (AMPL, stETH)
  → Blacklist? (USDC, USDT)
  → Missing return? (USDT)

□ DEX/AMM:
  → Pool liquidity sufficient?
  → Slippage protection?
  → Flash loan + swap = manipulation?

□ Bridge:
  → Trust model?
  → Replay protection?
  → Message ordering?
```

### PASS E: COLLISION (Spearbit-style)
```
Setelah semua pass selesai:

1. Review findings dari Pass A-D
2. CROSS-VALIDATE:
   → Finding dari Pass A + Pass C = stronger?
   → Missing check (A) + exploit path (C) = CRITICAL?
3. COMBINE complementary findings
4. DEBATE severity:
   → "Is this really HIGH or just MEDIUM?"
   → "Can this be exploited on mainnet NOW?"
   → "What's the concrete profit?"
5. PRIORITIZE by: impact × exploitability × probability
```

---

## STEP 4: PATTERN MATCHING (Hacken-style)
## Waktu: 30 min
## Goal: Check against known vulnerability database

```
□ ERC4626 inflation attack (donate + first depositor)
□ Reentrancy (single, cross-function, cross-contract, read-only)
□ Access control bypass (missing, wrong, initializer)
□ Oracle manipulation (spot price, TWAP, flash loan)
□ Flash loan governance (votingDelay=0, no threshold)
□ Proxy storage collision (upgrade, no gap)
□ Signature replay (missing nonce, chainId, expiry)
□ Sandwich attack (no slippage, public mempool)
□ Precision loss (division before multiplication)
□ Rounding exploitation (favor user instead of protocol)
□ Donation attack (balanceOf-based accounting)
□ Unbounded loop (gas DoS)
□ Timestamp dependence (block.timestamp ± 15s)
□ tx.origin authentication (phishing)
□ Selfdestruct (pre-Cancun: code deletion)
□ Delegatecall to untrusted (arbitrary code execution)
□ Unchecked return value (silent failure)
□ Front-running (commit-reveal missing)
□ Stale state (lazy update, no poke)
□ Cross-contract trust (callback abuse)

Untuk setiap pattern:
  → Ada di code ini? → flag
  → Udah di-mitigate? → verify mitigation correct
  → Novel variant? → investigate deeper
```

---

## STEP 5: FORMAL VERIFICATION (Quantstamp-style, critical paths only)
## Waktu: 1-2 jam
## Goal: PROVE properties for critical functions

```
Untuk 3-5 most critical functions:

1. Write specification:
   PRE:  require(balance >= amount)
         require(msg.sender == owner)
   POST: balance_after == balance_before - amount
         recipient_after == recipient_before + amount
   INV:  sum(balances) == totalSupply

2. Halmos symbolic test:
   function prove_withdraw_correct(uint256 amount) public {
       vm.assume(amount <= userBalance);
       uint256 before = vault.totalAssets();
       withdraw(amount);
       assert(vault.totalAssets() == before - amount);
   }

3. Echidna long fuzz (1M+ runs):
   echidna --test-limit 1000000

4. Result:
   → PROVEN: property holds for ALL inputs
   → COUNTEREXAMPLE: bug found, save as PoC
   → TIMEOUT: inconclusive, manual review needed
```

---

## STEP 6: REPORT (Industry Standard Format)
## Waktu: 2-4 jam
## Goal: Actionable, professional, verifiable

```
Untuk setiap finding:

## [SEVERITY-XX] Title

### Severity
CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL

### Summary
1 paragraph: what + why + impact

### Vulnerability Details
- Exact location (file:line)
- What code does vs what it should do
- Why exploitable

### Impact
- WHO loses? (users, protocol, LPs)
- HOW MUCH? (concrete numbers)
- CONDITIONS? (what must be true)
- PROBABILITY? (how likely)

### Proof of Concept
Foundry test (MUST be runnable):
  function test_Exploit() public {
      // Step-by-step attack
      // Assert: victim lost funds
  }

### Recommended Mitigation
Specific code fix:
  // Before:
  // After:

### References
- Similar past exploits
- OZ docs / EIP references
```

---

## STEP 7: FIX REVIEW
## Waktu: 1-2 jam
## Goal: Verify fix, check for regressions

```
□ Fix addresses ROOT CAUSE (not symptom)?
□ Fix applied to ALL instances of pattern?
□ Fix introduces NEW issues?
□ Re-run Slither → no new findings?
□ Re-run Echidna → properties still hold?
□ Re-run original PoC → now FAILS (fixed)?
□ Try VARIANTS of attack → also fail?
□ Fix changes behavior for legitimate users?
```

---

## QUICK REFERENCE: WHICH FIRM FOR WHICH STEP

```
Step 1 (Recon):        Halborn     — full attack surface
Step 2 (Automated):    ToB         — Slither/Echidna/Manticore
Step 3A (Architecture): Spearbit   — independent review
Step 3B (Functions):   Spearbit   — 25 questions per function
Step 3C (Economic):    Sherlock   — profit modeling
Step 3D (Dependencies): Quantstamp — formal trust analysis
Step 3E (Collision):   Spearbit   — cross-validate + combine
Step 4 (Patterns):     Hacken     — known vulnerability DB
Step 5 (Formal):       Quantstamp — prove/disprove properties
Step 6 (Report):       ALL        — industry standard format
Step 7 (Fix Review):   ToB        — re-test + variant attacks

Education:             Cyfrin     — learn fundamentals
Competition:           Sherlock   — practice in contests
```

---

## THE BOZAGENTIC RULE

```
Setiap audit WAJIB:
  ✅ Step 1-7 completed
  ✅ Minimum 3 invariants defined + tested
  ✅ Minimum 1 economic model with concrete numbers
  ✅ Every HIGH/CRITICAL has runnable PoC
  ✅ Every finding has specific code fix
  ✅ Fix review after remediation
  
TIDAK BOLEH:
  ❌ Report tanpa PoC
  ❌ Overclaim severity
  ❌ Report gas optimization sebagai finding
  ❌ Skip Step 3C (economic modeling)
  ❌ Skip Step 4 (pattern matching)
  ❌ Submit tanpa verify on-chain
```

---

*BOZAGENTIC · "7 firms. 1 framework. Zero excuses."*
