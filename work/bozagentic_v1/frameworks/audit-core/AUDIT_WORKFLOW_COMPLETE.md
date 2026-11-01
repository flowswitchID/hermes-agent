# COMPLETE AUDIT WORKFLOW — BOZAGENTIC
# Step-by-step: from scope to submission
# Last updated: 2026-08-01

---

## PHASE 0: RECON (30 min)

```
1. Read bounty page: scope, rewards, severity matrix, out-of-scope
2. Clone ALL repos in scope
3. Read README, docs, architecture diagrams
4. Map contract inheritance + dependencies
5. Check previous audits (don't re-report known issues)
6. Identify trust model: who is trusted, what can they do
7. List external dependencies: oracles, tokens, protocols
8. Check compiler version + known CVEs
```

## PHASE 1: AUTOMATED SCAN (30 min)

```
Run ALL tools in parallel:
  slither src/ --filter-paths "lib|test|script" --exclude-informational
  slither src/ --detect inconsistent-state-tracking,erc4626-inflation-attack
  semgrep --config defi-logic-rules.yaml --config exact-cashback-pattern.yaml src/
  aderyn .
  mythril analyze <main_contract> --solc-json settings.json --solv <version> -t 3
  forge test (existing tests)
```

## PHASE 2: LINE-BY-LINE (2-4 hours)

```
For EACH contract in scope:
  1. Read EVERY line (no grep/skim shortcuts)
  2. Map money flow: IN → contract → OUT
  3. Check access control on EVERY state-changing function
  4. Verify CEI pattern (Checks-Effects-Interactions)
  5. Check math: overflow, rounding, precision
  6. Check edge cases: 0, max, empty, first, last
  7. Verify events match state changes
  8. Check assembly blocks line by line
  9. Verify storage layout (packing, collisions)
  10. Check cross-contract assumptions
```

## PHASE 3: ECONOMIC MODELING (1 hour)

```
For EACH protocol:
  1. "Flash loan $1B — what can I exploit?"
  2. "Manipulate oracle 50% — profit?"
  3. "I'm malicious admin — max damage?"
  4. "I'm first user — can I rug others?"
  5. "Front-run every tx — profit per tx?"
  6. "Donate 1 wei — what breaks?"
  7. "Call public sync/update — effect?"
  8. "Governance attack — cost vs profit?"
  9. "Sandwich user — max extractable?"
  10. "I'm protocol B — can I exploit A?"
```

## PHASE 4: CROSS-PROTOCOL (1 hour)

```
For EACH pair of interacting contracts:
  1. Map the interaction (who calls whom, with what data)
  2. List assumptions each makes about the other
  3. Break each assumption: "what if this changes?"
  4. Check reentrancy across the boundary
  5. Check amount bounds at every layer
  6. Verify hash/nonce uniqueness across protocols
```

## PHASE 5: FORMAL VERIFICATION (1 hour)

```
For each suspicious finding:
  1. Z3: Write BitVec/Int proof (SAT = bug, UNSAT = safe)
  2. Halmos: Write symbolic property (minimal project!)
  3. Echidna: Write targeted invariant (should FAIL if bug)
  4. Foundry: Write PoC test (must PASS to confirm)
  5. Medusa: Run assertion testing (50K+ calls)
```

## PHASE 6: BYTECODE VERIFICATION (30 min)

```
For deployed contracts:
  1. Verify source matches bytecode (Blockscout/Etherscan)
  2. Check storage layout (forge inspect storageLayout)
  3. Verify function selectors in deployed bytecode
  4. Check proxy pattern (EIP-1967 slot)
  5. Decode reentrancy guard mechanism
  6. Verify storage packing (Z3 proof)
```

## PHASE 7: SEVERITY CALIBRATION

```
CRITICAL: Permissionless + profitable + irreversible
HIGH:     Permissionless + profitable OR privileged + catastrophic
MEDIUM:   Conditional + moderate impact OR trusted role + bypass
LOW:      Minimal impact, theoretical, or code quality
INFO:     Best practice, no security impact

NEVER submit:
  - Design choices without security impact
  - User error scenarios
  - Issues requiring leaked keys
  - Theoretical without practical PoC
  - Gas optimization suggestions
  - Centralization risks (unless explicitly in scope)
```

## PHASE 8: REPORT + SUBMISSION

```
Report must include:
  1. Title (no parentheses, clear and specific)
  2. Severity (calibrated, honest)
  3. Summary (2-3 sentences)
  4. Vulnerability details (exact code, line numbers)
  5. Attack scenario (step by step)
  6. Impact (quantified if possible)
  7. PoC (Foundry test, MUST pass)
  8. Recommended fix (exact code change)
  9. Tools used (list all)

Submission:
  - Paste PoC inline (don't just attach)
  - Target asset: specific contract name
  - Double-check scope before submitting
```

---

## TOOL CHEAT SHEET

```
TOOL          | COMMAND
══════════════|══════════════════════════════════════════
Slither       | slither src/ --filter-paths "lib|test|script"
Slither custom| slither src/ --detect inconsistent-state-tracking
Semgrep       | semgrep --config rules.yaml src/
Aderyn        | aderyn .
Mythril       | mythril analyze X.sol --solc-json s.json --solv 0.8.29 -t 3
Foundry test  | forge test -vv
Foundry fuzz  | forge test --fuzz-runs 10000
Echidna       | echidna test.t.sol --contract X --config c.yaml
Medusa        | medusa fuzz --config m.json
Halmos        | halmos --contract X --solver-timeout-assertion 10000
Z3            | python3 proof.py
Blockscout    | curl blockscout API for source
cast          | cast storage/code/call for on-chain
forge inspect | forge inspect X storageLayout/methodIdentifiers
```

---

## RED FLAGS (instant deep dive)

```
🔴 balanceOf() in vault accounting → inflation attack
🔴 Public sync()/update()/skim() → donation attack
🔴 No slippage protection → sandwich
🔴 Oracle without staleness check → manipulation
🔴 Admin drain without limit → rug
🔴 Governance without snapshot → flash loan vote
🔴 Reward without time lock → flash loan claim
🔴 delegatecall to non-immutable → storage hijack
🔴 selfdestruct reachable → forced ether
🔴 tx.origin auth → phishing
🔴 Inconsistent state tracking → cap bypass
🔴 Cross-protocol assumption without verification
🔴 abi.encodePacked with multiple dynamic types → hash collision
🔴 Unchecked external call return → silent failure
🔴 Loop over unbounded external array → DoS
```
