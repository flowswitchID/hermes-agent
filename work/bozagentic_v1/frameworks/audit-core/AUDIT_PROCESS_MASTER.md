# HOW TOP FIRMS ACTUALLY AUDIT — STEP-BY-STEP PROCESS
# Bukan profil company. Ini CARA KERJA mereka.
# BOZAGENTIC · 2026-07-30

---

## PHASE 0: BEFORE TOUCHING CODE (All Firms)

### 0.1 — Understand the Protocol FIRST
```
Sebelum baca 1 baris code pun:

1. Baca docs/whitepaper
   → Apa yang protokol INGIN lakukan?
   → Siapa user-nya?
   → Duit mengalir dari mana ke mana?

2. Gambar flow diagram
   → User deposit → vault → yield → withdraw
   → Borrow → collateral → liquidation → repay
   → Kalau nggak bisa gambar flow-nya, belum ngerti

3. Identifikasi trust assumptions
   → Siapa yang dipercaya? (admin, oracle, keeper)
   → Apa yang bisa mereka lakukan?
   → Apa yang terjadi kalau mereka jahat/rugi?

4. Identifikasi invariants
   → Apa yang HARUS selalu true?
   → Contoh: totalShares <= totalAssets
   → Contoh: user nggak bisa withdraw > deposit
   → Contoh: 1 share selalu >= 1 asset

5. Tanya ke protocol team:
   → "Apa yang paling lo takutin?"
   → "Apa yang nggak boleh terjadi?"
   → "Siapa yang punya akses admin?"
```

### 0.2 — Scope Definition
```
Tentukan BATASAN:

IN SCOPE:
  - Contract addresses / file paths
  - Specific functions
  - External dependencies (oracle, DEX, bridge)

OUT OF SCOPE:
  - Frontend
  - Deploy scripts
  - Test files
  - Third-party contracts (OZ, Solmate)
  - Known issues (listed by team)

RULE: Kalau nggak di scope, JANGAN report.
      Tapi kalau nemu bug critical di dependency → bilang.
```

---

## PHASE 1: AUTOMATED SCAN (30 min - 2 hours)

### 1.1 — Trail of Bits Approach
```bash
# Step 1: Slither (static analysis)
slither . --print human-summary
slither . --detect reentrancy-eth,reentrancy-no-eth,unchecked-transfer
slither . --detect arbitrary-send,unprotected-upgrade
slither . --detect uninitialized-state,uninitialized-local

# Step 2: Slither taint analysis (data flow)
slither . --detect unchecked-lowlevel
slither . --print data-dependency    # variable dependency graph
slither . --print inheritance-graph  # contract hierarchy

# Step 3: Echidna (fuzzing) — write properties FIRST
# File: Invariants.sol
contract Invariants {
    // Property: totalSupply selalu == sum of balances
    function echidna_supply_conservation() public returns (bool) {
        return token.totalSupply() == sum_of_all_balances;
    }
    
    // Property: user nggak bisa withdraw > deposit
    function echidna_no_profit() public returns (bool) {
        return userBalance <= userDeposit;
    }
}
echidna Invariants.sol --contract Invariants --test-mode assertion

# Step 4: Manticore (symbolic execution) — for critical paths
manticore Contract.sol --detect integer-overflow
manticore Contract.sol --explore  # explore all paths
```

### 1.2 — Spearbit Approach
```
Mereka JARANG rely di automated tools.
Tapi kalau pake:

1. Slither untuk QUICK TRIAGE
   → Bukan untuk final findings
   → Untuk identify "hot spots"
   → Focus manual review ke flagged areas

2. Foundry fuzz tests
   → Tulis test untuk setiap invariant
   → forge test --fuzz-runs 100000
   → Cari edge cases

3. Halmos untuk symbolic proof
   → Prove access control properties
   → Prove arithmetic bounds
   → "Can this function EVER be called by non-owner?"
```

### 1.3 — What Automated Tools CATCH vs MISS
```
CATCH (80% automated):
  ✅ Unchecked external call return values
  ✅ Missing access control (public mint/burn)
  ✅ Reentrancy patterns (standard)
  ✅ Uninitialized storage pointers
  ✅ Selfdestruct usage
  ✅ tx.origin authentication
  ✅ Deprecated Solidity patterns

MISS (requires human):
  ❌ Business logic errors
  ❌ Economic attacks (inflation, sandwich)
  ❌ Cross-contract trust assumptions
  ❌ Oracle manipulation scenarios
  ❌ Governance attack vectors
  ❌ Rounding direction exploitation
  ❌ Composability issues (protocol A + protocol B)
  ❌ "Technically correct but economically broken"
```

---

## PHASE 2: MANUAL REVIEW — THE REAL WORK (days to weeks)

### 2.1 — First Pass: Architecture Review (2-4 hours)
```
Baca code dari ATAS ke BAWAH:

1. Constructor / Initializer
   → Apa yang di-set saat deploy?
   → Siapa owner/admin?
   → Ada _disableInitializers()?
   → Storage layout (untuk upgradeable)

2. State Variables
   → Apa yang disimpan?
   → Mapping vs array?
   → Packed structs?
   → Storage gaps?

3. Modifiers
   → Access control: who can call what?
   → State guards: whenNotPaused, whenNotLocked
   → Reentrancy: nonReentrant on what?

4. External Functions (public API)
   → List SEMUA external/public functions
   → Group by: user-facing, admin-only, keeper-only, callback
   → Ini attack surface lo

5. Internal Functions
   → Core logic
   → Math operations
   → State transitions

6. Events
   → Apa yang di-emit?
   → Ada yang MISSING? (state change tanpa event = red flag)
```

### 2.2 — Second Pass: Function-by-Function (days)
```
Untuk SETIAP external function, tanya:

ACCESS CONTROL:
  □ Siapa yang bisa call?
  □ Ada modifier? (onlyOwner, onlyRole, nonReentrant)
  □ Bisa di-call oleh contract lain? (callback attack)
  □ Apa yang terjadi kalau msg.sender = address(0)?

INPUT VALIDATION:
  □ Parameter = 0? → revert atau silent?
  □ Parameter = type(uint256).max? → overflow?
  □ Array length mismatch? → revert?
  □ Address = address(0)? → burn atau stuck?

STATE CHANGES:
  □ Apa yang berubah?
  □ Urutan: state update BEFORE atau AFTER external call?
  □ Ada reentrancy window?
  □ Bisa di-call 2x dalam 1 tx? (double-spend)

EXTERNAL CALLS:
  □ Call ke mana?
  □ Return value di-check?
  □ Bisa revert? → DoS?
  □ Bisa re-enter? → reentrancy?
  □ Trust assumption: target contract bisa jahat?

MATH:
  □ Rounding direction? (Floor/Ceil — favor siapa?)
  □ Division before multiplication? (precision loss)
  □ mulDiv vs sequential? (overflow risk)
  □ Fixed-point: berapa decimals? Consistent?

TOKEN FLOWS:
  □ Token masuk dari mana?
  □ Token keluar ke mana?
  □ Balance check: balanceOf() vs stored value?
  □ Fee-on-transfer token? → accounting broken?
  □ Rebasing token? → balance changes tanpa transfer?
```

### 2.3 — Third Pass: Cross-Function Analysis (hours)
```
Setelah baca individual functions:

1. INTERACTION antara functions
   → Bisa call A lalu B dalam 1 tx untuk exploit?
   → State dari A mempengaruhi B secara unexpected?
   → Flash loan: borrow → call A → call B → repay?

2. STATE MACHINE
   → Gambar semua possible states
   → Transisi mana yang valid?
   → Ada state yang "stuck"? (no way out)
   → Bisa skip state? (A → C tanpa B)

3. RACE CONDITIONS
   → Front-running: lihat tx di mempool → frontrun
   → Sandwich: frontrun + backrun
   → Time-dependent: block.timestamp manipulation

4. ECONOMIC MODELING
   → Simulate dengan angka konkret
   → "Kalau gue deposit 1 wei, lalu donate 100 ETH..."
   → "Kalau gue borrow max, lalu price drop 50%..."
   → "Kalau semua user withdraw simultaneously..."
```

### 2.4 — Fourth Pass: External Dependencies (hours)
```
Untuk SETIAP external contract yang di-call:

1. ORACLE
   → Source: Chainlink? Uniswap TWAP? Custom?
   → Staleness: ada heartbeat check?
   → Manipulation: bisa di-manipulasi dalam 1 tx?
   → Fallback: apa yang terjadi kalau oracle down?

2. DEX / AMM
   → Pool mana yang dipake?
   → Liquidity cukup?
   → Slippage protection?
   → Flash loan + swap = price manipulation?

3. TOKEN
   → Standard ERC20? Atau ada quirks?
   → Fee-on-transfer? (USDT, PAXG)
   → Rebasing? (AMPL, stETH)
   → Missing return value? (USDT)
   → Blacklist? (USDC, USDT)

4. BRIDGE / CROSS-CHAIN
   → Trust model: siapa yang validate?
   → Replay protection?
   → Message ordering?
```

---

## PHASE 3: SPECIFIC ATTACK PATTERNS (checklist)

### 3.1 — Trail of Bits Checklist
```
□ Reentrancy (single + cross-function + cross-contract)
□ Access control (missing, wrong, bypassable)
□ Integer overflow/underflow (pre-0.8 or unsafe cast)
□ Unchecked return values
□ Front-running / MEV
□ Oracle manipulation
□ Denial of Service (gas, revert, panic)
□ Uninitialized storage
□ Delegatecall to untrusted
□ Selfdestruct (pre-Cancun)
□ Signature replay (missing nonce/chainId)
□ Flash loan attacks
□ Governance attacks
□ Sandwich attacks
□ Rounding exploitation
□ Donation/inflation attacks (ERC4626)
□ Proxy storage collision
□ Initializer re-initialization
□ Timestamp dependence
□ tx.origin authentication
□ Unbounded loops (gas DoS)
□ Missing slippage protection
□ Incorrect fee calculation
□ Precision loss in division
□ Stale state (lazy update exploits)
```

### 3.2 — Spearbit "What Would Break" Approach
```
Untuk setiap function, tanya:

"BAGAIMANA kalau..."
  ...user call ini dengan amount = 0?
  ...user call ini dengan amount = max uint?
  ...user call ini 100x dalam 1 tx?
  ...user call ini dari contract (bukan EOA)?
  ...user frontrun tx ini?
  ...admin key compromised?
  ...oracle return 0?
  ...oracle return max uint?
  ...token transfer revert?
  ...token transfer return false (tanpa revert)?
  ...external call consume semua gas?
  ...contract di-call sebelum initialize?
  ...contract di-upgrade ke malicious impl?
  ...2 user call simultaneously?
  ...protocol punya 0 liquidity?
  ...protocol punya max liquidity?
```

### 3.3 — Quantstamp Formal Approach
```
Untuk critical functions, tulis SPECIFICATION:

Pre-conditions:
  - require(balance >= amount)
  - require(msg.sender == owner)
  - require(!paused)

Post-conditions:
  - balance_after == balance_before - amount
  - recipient_balance_after == recipient_before + amount
  - totalSupply unchanged

Invariants (ALWAYS true):
  - sum(balances) == totalSupply
  - totalAssets >= totalShares (for vaults)
  - no user can have negative balance
  - admin functions require authorization

Kalau bisa PROVE invariant violated → CRITICAL
Kalau bisa SHOW scenario → HIGH/MEDIUM
Kalau cuma THEORETICAL → LOW/INFO
```

---

## PHASE 4: WRITING THE REPORT

### 4.1 — Finding Format (Industry Standard)
```markdown
## [H-01] Title: Short description of the bug

### Severity: HIGH

### Summary
One paragraph: what's wrong + why it matters.

### Vulnerability Details
Technical explanation:
- Exact code location (file:line)
- What the code does
- What it SHOULD do
- Why the difference is exploitable

### Impact
Concrete impact:
- Who loses money?
- How much? (with numbers)
- Under what conditions?
- How likely is exploitation?

### Proof of Concept
Runnable code (Foundry test preferred):
```solidity
function test_Exploit() public {
    // Step 1: ...
    // Step 2: ...
    // Assert: victim lost funds
}
```

### Recommended Mitigation
Specific fix with code:
```solidity
// Before (vulnerable):
function vulnerable() { ... }

// After (fixed):
function fixed() { ... }
```
```

### 4.2 — Severity Justification
```
CRITICAL = ALL of:
  ✅ Direct fund loss
  ✅ No special access needed
  ✅ Exploitable on mainnet NOW
  ✅ High probability of occurrence

HIGH = 3 of 4:
  ✅ Direct fund loss OR protocol broken
  ✅ Requires specific conditions
  ✅ Exploitable with reasonable effort
  ✅ Medium probability

MEDIUM = 2 of 4:
  ✅ Limited loss OR requires privileged access
  ✅ Multiple conditions needed
  ✅ Theoretical but plausible
  ✅ Low probability

LOW = 1 of 4:
  ✅ Minimal impact
  ✅ Best practice violation
  ✅ Unlikely to be exploited
  ✅ Informational with minor security implication
```

### 4.3 — Common Mistakes in Reports
```
❌ "This could potentially maybe lead to loss of funds"
   → Vague. Give CONCRETE scenario with NUMBERS.

❌ "Missing access control on setFee()"
   → Is setFee() actually dangerous? What's the IMPACT?
   → If fee can be set to 100% → HIGH
   → If fee can be set to 0% → LOW (protocol loses revenue, not users)

❌ Reporting gas optimizations as findings
   → "Use unchecked{} here" → NOT a security finding
   → Unless: gas DoS is the attack vector

❌ Overclaiming severity
   → "CRITICAL: missing event emission"
   → No. That's INFORMATIONAL.
   → Triager will downgrade → you lose credibility

❌ No PoC
   → "I think this might be exploitable"
   → Without PoC → triager can't verify → likely dismissed
```

---

## PHASE 5: FIX REVIEW

### 5.1 — How Firms Verify Fixes
```
1. Read the fix
   → Does it address the ROOT CAUSE?
   → Or just the symptom?

2. Check for NEW issues
   → Does the fix introduce reentrancy?
   → Does it break other functions?
   → Does it change behavior unexpectedly?

3. Re-run automated tools
   → Slither on fixed code
   → Echidna properties still pass?

4. Re-test attack scenario
   → Original PoC should now FAIL
   → Try VARIANTS of the attack
   → Can the fix be bypassed?

5. Check consistency
   → Same pattern elsewhere in codebase?
   → Fix applied to ALL instances?
```

---

## PHASE 6: FIRM-SPECIFIC TECHNIQUES

### Trail of Bits: Property-Based Testing
```
Mereka tulis PROPERTIES sebelum audit:

// Properties for a lending protocol:
1. Total borrows <= Total deposits (solvency)
2. Interest rate always >= 0
3. Liquidation always profitable for liquidator
4. No user can borrow without collateral
5. Admin can't drain user funds directly

Lalu: Echidna fuzzes untuk VIOLATE properties
Kalau Echidna nemu counterexample → BUG CONFIRMED
```

### Spearbit: Independent → Collision
```
1. 3-5 auditors review INDEPENDENTLY (no communication)
2. Each writes their own findings
3. "Collision" meeting: share all findings
4. Cross-validate: "I found X" → "Yes, and I found it leads to Y"
5. Combine complementary findings into stronger reports
6. Debate severity until consensus

WHY this works:
  → Auditor A notices missing check
  → Auditor B notices the function that exploits it
  → Together: CRITICAL finding
  → Alone: both would rate MEDIUM
```

### Cyfrin: Invariant-First
```
1. Define invariants BEFORE reading code
2. Write Foundry invariant tests
3. Run fuzz: forge test --fuzz-runs 1000000
4. If invariant breaks → investigate WHY
5. Root cause = the bug

Example:
  invariant: vault.totalAssets() >= vault.totalSupply()
  → Fuzz finds: after donate + withdraw, assets < supply
  → Root cause: donate inflates without minting shares
  → Bug: inflation attack
```

### Sherlock: Economic Modeling
```
1. Model the protocol as a SYSTEM
2. Identify all value flows
3. For each flow: can value be extracted unfairly?
4. Simulate with concrete numbers:
   "If TVL = $10M, and attacker has $100K..."
   "Can they extract > $100K?"
5. If yes → profitable attack → finding

Focus: ECONOMIC PROFITABILITY
  → Not just "technically possible"
  → But "is it PROFITABLE after gas + capital cost?"
```

### Quantstamp: Formal Specification
```
1. Write formal spec in SMT-LIB or Certora
2. Define: pre-conditions, post-conditions, invariants
3. Model checker explores ALL possible inputs
4. If ANY input violates spec → counterexample = bug
5. If NO input violates → PROVEN SAFE (for that property)

Advantage: MATHEMATICAL CERTAINTY
  → Not "I tested 1M cases"
  → But "I proved ALL cases"
Disadvantage: EXPENSIVE + time-consuming
  → Only for critical paths
```

### Halborn: Attack Surface Mapping
```
1. Map EVERY entry point:
   → Smart contracts (external functions)
   → APIs (REST, GraphQL)
   → Frontend (JavaScript, browser)
   → Infrastructure (servers, cloud)
   → Human (social engineering)

2. For each entry point:
   → What can an attacker do?
   → What's the worst case?
   → What's the detection time?

3. Prioritize by: impact × probability
4. Attack the highest-priority paths first

WHY: Most hacks are NOT contract bugs
  → 2023: $1.7B lost
  → ~60% from contract exploits
  → ~40% from infra/social/key compromise
```

### Hacken: Pattern Matching + Manual
```
1. Run Slither + Mythril
2. Match findings against KNOWN PATTERNS:
   → "This looks like the Beanstalk governance attack"
   → "This is the same as Euler's donateToReserve"
3. Manual review for protocol-specific logic
4. Report with references to similar past exploits

STRENGTH: Fast, catches known patterns
WEAKNESS: Misses novel attacks
```

---

## SUMMARY: THE AUDIT MINDSET

```
Junior auditor thinks:
  "Is this code CORRECT?"

Senior auditor thinks:
  "How can I BREAK this code?"

Elite auditor thinks:
  "How can I make money from this code?"
```

### The 3 Questions for Every Function:
```
1. WHO can call this? (access control)
2. WHAT happens if I call it with weird inputs? (edge cases)
3. HOW can I profit from calling it? (economic incentive)
```

### The Audit Priority Pyramid:
```
        /\
       /  \      CRITICAL: Fund loss, no access needed
      /    \
     / HIGH \    HIGH: Fund loss, conditions needed
    /--------\
   /  MEDIUM  \  MEDIUM: Limited loss, privileged access
  /------------\
 /     LOW      \ LOW: Best practice, minimal impact
/----------------\
/  INFORMATIONAL  \ INFO: Code quality, no security impact
/------------------\
```

---

*BOZAGENTIC · "The bug is never where you first look. It's where two correct things interact incorrectly."*
