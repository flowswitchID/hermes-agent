# Flying Tulip Bug Bounty #248 — Audit Submission

## Finding: Spark Savings Vault Withdrawal Caps Lock 35-48% of PUT Collateral

**Severity:** MEDIUM (honest assessment — LOW-MEDIUM)
**Duplicate risk:** ~50% (similar class as AAVE-01)
**Expected value:** ~$2,800

## How to run PoC

```bash
cd poc/
# Need Foundry installed
forge init --no-git --force .
# Copy SparkWithdrawalCapPoC.t.sol to test/
forge test --match-contract SparkWithdrawalCapPoC -vvv \
  --fork-url https://ethereum-rpc.publicnode.com
```

Expected: 8/8 PASS

## Folder structure

```
report/          — Submission report (paste into Sherlock)
poc/             — Foundry fork tests (8 proofs)
source/          — Contract source code (from Blockscout)
tools-output/    — Aderyn/Slither/Semgrep results
```

## Tools used

| Tool | Result |
|------|--------|
| Slither (built-in + 5 custom) | 0 real findings |
| Semgrep (5 rules) | 0 real findings |
| Aderyn (88 detectors) | 4 HIGH → 0 real |
| Echidna (50K runs) | ALL PASS |
| Medusa (50K runs) | 14/14 PASS |
| Halmos (symbolic) | 4/5 PASS |
| Z3 (SMT solver) | 6/6 PROVEN |
| Foundry fuzz (50K) | ALL PASS |
| Fork tests (5 chains) | 30+ PASS |
| Flash loan (8 vectors) | 0 exploitable |
| Invariants (8 checks) | 7/8 PASS |

## Honest assessment

- Finding is TECHNICALLY VALID (on-chain proof)
- But WEAK: same class as AAVE-01, authorized role action,
  funds delayed not lost, canDivest() correctly warns
- NOT HIGH. No direct fund loss. No permissionless profit.
- Submit at your own risk — 50% chance duplicate rejection
