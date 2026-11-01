# Audit-Core Framework

Smart contract audit & formal verification framework.

## Components

### Static Analysis
- Slither — static analysis framework
- Aderyn — Rust-based Solidity analyzer
- Manual review patterns

### Formal Verification
- **Z3 Prover** — SMT solver for constraint solving
  - Rounding proofs, cashback invariant, buildercodes
- **Halmos** — symbolic testing for Foundry
  - ERC-4626 property tests, lending protocol invariants
- **Echidna** — fuzzing framework
  - Fuzz configs, harness contracts

### Dynamic Analysis
- **Mythril** — symbolic execution, security analysis
  - Custom detectors: reentrancy, access control, flash loan, oracle manipulation
- **Foundry** — forge tests, invariant tests

### Audit Reports
- Real audit reports from: Arcadia, Kelp DAO, EigenLayer, Usual Labs, Basin
- Bug report studies: Sherlock contests (2025)

### Methodology
- AUDIT_PROCESS_MASTER.md — step-by-step audit workflow
- AUDIT_WORKFLOW_COMPLETE.md — complete audit pipeline
- ECONOMIC_ATTACK_MASTER.md — economic attack vectors
- EVM_BYTECODE_MASTER.md — bytecode-level analysis
