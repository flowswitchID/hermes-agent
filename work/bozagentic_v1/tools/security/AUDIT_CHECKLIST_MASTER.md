# COMPLETE AUDIT CHECKLIST — BOZAGENTIC
# Every audit MUST go through this checklist
# Last updated: 2026-08-01

---

## PHASE 1: RECON (5 min)

- [ ] Read README, docs, scope definition
- [ ] Identify all contracts in scope
- [ ] Map inheritance chain
- [ ] List external dependencies (oracles, tokens, protocols)
- [ ] Check compiler version + known CVEs
- [ ] Check previous audits (don't re-report known issues)
- [ ] Identify trust model (who is trusted, what can they do)

## PHASE 2: SURFACE SCAN (10 min per contract)

- [ ] List ALL external/public functions (attack surface)
- [ ] Map money flow (IN → contract → OUT)
- [ ] Identify access control (modifiers, roles)
- [ ] Check for payable functions
- [ ] Check for delegatecall / selfdestruct
- [ ] Check for assembly blocks
- [ ] List events (what state changes are emitted)

## PHASE 3: PATTERN SCAN (10 min per contract)

### 10 Economic Attack Patterns:
- [ ] P1: balanceOf in vault accounting → inflation attack
- [ ] P2: Governance without snapshot → flash loan vote
- [ ] P3: Spot oracle + thin liquidity → manipulation
- [ ] P4: Token callbacks (ERC777/1363) → reentrancy
- [ ] P5: Donation to inflate share price → first depositor
- [ ] P6: Per-function reentrancy guard → cross-function
- [ ] P7: Div before mul → rounding exploit
- [ ] P8: Oracle without staleness check → stale price
- [ ] P9: EIP-712 without chainId → cross-chain replay
- [ ] P10: Admin without limit/timelock → rug

### 10 Code Patterns:
- [ ] Unchecked external call return value
- [ ] tx.origin for authentication
- [ ] Unbounded loop over external array
- [ ] Missing zero-address check
- [ ] Integer overflow/underflow (pre-0.8)
- [ ] Signature malleability (s value)
- [ ] Front-running sensitive operations
- [ ] Storage collision in proxy pattern
- [ ] Uninitialized storage pointer
- [ ] Incorrect use of abi.encodePacked (hash collision)

## PHASE 4: DEEP DIVE (30+ min per contract)

### Manual Line-by-Line:
- [ ] Read EVERY function, EVERY line
- [ ] Trace state changes for each operation
- [ ] Verify CEI pattern (Checks-Effects-Interactions)
- [ ] Check all math operations (overflow, rounding, precision)
- [ ] Verify access control on EVERY state-changing function
- [ ] Check edge cases: 0, max, empty, first, last
- [ ] Verify events match state changes

### Cross-Protocol:
- [ ] Map all external calls
- [ ] List assumptions about each dependency
- [ ] Break each assumption: "what if this changes?"
- [ ] Check: can dependency be upgraded?
- [ ] Check: can dependency re-enter?
- [ ] Check: can dependency return unexpected values?

### Economic:
- [ ] "Flash loan $1B — what can I exploit?"
- [ ] "Manipulate oracle 50% — profit?"
- [ ] "I'm malicious admin — max damage?"
- [ ] "I'm first user — can I rug others?"
- [ ] "Front-run every tx — profit per tx?"
- [ ] "Donate 1 wei — what breaks?"
- [ ] "Call public sync/update — effect?"
- [ ] "Governance attack — cost vs profit?"
- [ ] "Sandwich user — max extractable?"
- [ ] "I'm protocol B — can I exploit A?"

## PHASE 5: TOOL MATRIX

### Automated (run ALL):
- [ ] Slither (built-in + custom detectors)
- [ ] Semgrep (custom rules)
- [ ] Aderyn
- [ ] Mythril (symbolic execution)
- [ ] Foundry tests (existing)
- [ ] Foundry fuzz (10K+ runs)
- [ ] Foundry invariant
- [ ] Echidna (50K+ runs, corpus, shrink)
- [ ] Medusa (50K+ runs, coverage-guided)
- [ ] Halmos (symbolic properties)
- [ ] Z3 SMT (mathematical proofs)

### Manual:
- [ ] Line-by-line review (100% of in-scope code)
- [ ] Cross-protocol interaction analysis
- [ ] Economic attack modeling
- [ ] Bytecode verification (for deployed contracts)
- [ ] Storage layout analysis (for proxies)

## PHASE 6: VALIDATION

For each finding:
- [ ] Write PoC (Foundry test, MUST pass)
- [ ] Verify severity (Impact × Likelihood matrix)
- [ ] Check if it's in scope
- [ ] Check if it's a duplicate
- [ ] Check if it's "by design" / documented
- [ ] Verify external attacker path exists
- [ ] Calculate actual profit / impact
- [ ] Write clear report with fix recommendation

## PHASE 7: SEVERITY CALIBRATION

```
CRITICAL: Permissionless + profitable + irreversible
HIGH:     Permissionless + profitable OR privileged + catastrophic
MEDIUM:   Conditional + moderate impact OR trusted role + bypass
LOW:      Minimal impact, theoretical, or code quality
INFO:     Best practice, no security impact
```

### NEVER submit:
- Design choices without security impact
- User error scenarios
- Issues requiring leaked keys
- Theoretical without practical PoC
- Gas optimization suggestions
- Centralization risks (unless explicitly in scope)

---

## SPEED TARGETS

```
Contract size    | Target time
< 200 lines      | 15 min
200-500 lines    | 30 min
500-1000 lines   | 60 min
> 1000 lines     | 90+ min (split into modules)
```

## RED FLAGS (instant deep dive)

```
🔴 balanceOf() in accounting
🔴 Public sync()/update()/skim()
🔴 No slippage protection
🔴 Oracle without staleness check
🔴 Admin drain without limit
🔴 Governance without snapshot
🔴 Reward without time lock
🔴 delegatecall to non-immutable
🔴 selfdestruct reachable
🔴 tx.origin auth
🔴 Inconsistent state tracking across operations
🔴 Cross-protocol assumption without verification
```
