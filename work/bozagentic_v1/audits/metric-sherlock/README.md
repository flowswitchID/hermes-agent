# Metric OMM — Sherlock Contest #1279 Audit Submission

## Finding: OracleBase Blacklist Bypass via Permissionless register()

**Severity:** MEDIUM
**Contract:** OracleBase (smart-contracts-poc/contracts/oracles/providers/OracleBase.sol)
**Function:** register() (lines 201-213)

## Contents

```
├── README.md
├── report/
│   └── BlacklistBypass_Report.md    ← Full report (paste to Sherlock)
├── poc/
│   └── BlacklistBypassPoC.t.sol     ← 5 proofs (forge test)
├── source/
│   └── OracleBase.sol               ← Vulnerable contract
└── tools-output/
    └── aderyn-report.md
```

## Run PoC

```bash
# In any Foundry project with forge-std:
forge test --match-contract BlacklistBypassPoC -vvv
```

Expected: 5/5 PASS

## Tools Used

| Tool | Result |
|------|--------|
| Slither (101 detectors) | Clean |
| Semgrep (5 custom rules) | 7 noise |
| Aderyn (88 detectors) | 3 HIGH = ALL FP |
| Echidna 50K | 5/5 PASS |
| Medusa 50K | 5/5 PASS |
| Foundry fuzz 10K | ALL PASS |
| Z3 SMT | 6/6 PROVEN |
| Mythril | 0 issues |
| Foundry test | 213/213 PASS |
| Manual review | ~7,000 lines, 3 repos |
