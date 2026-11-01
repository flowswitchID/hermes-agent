# CTF DRILL LOG — Vulnerable Lending Pool
# BOZAGENTIC | 2026-08-01

---

## EXERCISE: VulnerableLending (3 bugs)

### Bug 1: CEI Violation in withdraw()
```solidity
// VULNERABLE:
token.transfer(msg.sender, amount); // external call FIRST
deposits[msg.sender] -= amount;     // state update SECOND

// FIXED:
deposits[msg.sender] -= amount;     // state FIRST
totalDeposits -= amount;
token.transfer(msg.sender, amount); // external call SECOND
```
- Detected by: Semgrep CEI rule ✅
- Exploit: Reentrancy via token callback
- Severity: HIGH (permissionless drain)

### Bug 2: No Collateral Check in borrow()
```solidity
// VULNERABLE:
function borrow(uint256 amount) external {
    require(totalBorrows + amount <= totalDeposits); // only liquidity
    borrows[msg.sender] += amount;
    token.transfer(msg.sender, amount);
}

// FIXED:
function borrow(uint256 amount) external {
    uint256 maxBorrow = collateral[msg.sender] * 100 / 150;
    require(borrows[msg.sender] + amount <= maxBorrow);
    ...
}
```
- Detected by: Echidna invariant ✅, Z3 proof ✅
- Exploit: Borrow entire liquidity with zero collateral
- Severity: CRITICAL (permissionless drain)

### Bug 3: Donation Attack via sync()
```solidity
// VULNERABLE:
function sync() external {
    uint256 balance = token.balanceOf(address(this));
    totalDeposits += excess; // inflates total, not individual
}

// FIXED: Remove sync() entirely. Internal accounting is truth.
```
- Detected by: Manual review ✅
- Exploit: Donate tokens → inflate totalDeposits → inconsistency
- Severity: MEDIUM (accounting corruption)

---

## TOOL RESULTS

```
TOOL          | VULNERABLE | FIXED
══════════════|════════════|══════
Foundry test  | 3/3 PASS   | 5/5 PASS
Echidna 10K   | BUG FOUND  | PASS
Semgrep CEI   | DETECTED   | CLEAN
Z3 proof      | SAT (bug)  | UNSAT (safe)
Slither       | 0 (FP)     | 0
```

## LESSONS

1. Echidna invariant must match the ACTUAL bug (not just solvency)
2. Slither detector needs precise IR matching (lvalue vs read)
3. Semgrep excels at syntactic patterns (CEI)
4. Z3 excels at mathematical proofs (collateral ratio)
5. Manual review catches what tools miss (donation attack)
