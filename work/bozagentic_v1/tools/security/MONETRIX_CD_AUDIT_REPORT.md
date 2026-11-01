# MONETRIX — AUDIT REPORT (Consensys Diligence Format)
# BOZAGENTIC · 2026-07-30
# Methodology: CD Step 0-4 applied end-to-end

---

## 1. Executive Summary

This report presents the results of applying the Consensys Diligence methodology
to Monetrix, a yield layer for Hyperliquid that funnels yield sources into a
unified stablecoin (USDM) with staking (sUSDM).

The review covered MonetrixVault (627 lines), MonetrixAccountant (345 lines),
MonetrixConfig (219 lines), TokenMath (98 lines), and supporting contracts.

**Tools used:** Scribble (annotation + instrumentation), Echidna (50K fuzz),
Mythril (symbolic execution), manual state machine analysis.

**Overall assessment:** The codebase is well-structured with defense-in-depth
(4-gate yield settlement, dual pause, timelocked governance). However, several
operator-trust assumptions create risk if the operator key is compromised.

**Recommendation:** Deploy with monitoring + bug bounty. Operator actions should
be monitored on-chain with alerting for anomalous patterns.

---

## 2. Scope

```
Repository:  github.com/code-423n4/2026-04-monetrix
Contracts:   src/core/MonetrixVault.sol (627 lines)
             src/core/MonetrixAccountant.sol (345 lines)
             src/core/MonetrixConfig.sol (219 lines)
             src/core/TokenMath.sol (98 lines)
             src/core/RedeemEscrow.sol (82 lines)
             src/core/YieldEscrow.sol (54 lines)
             src/core/InsuranceFund.sol (55 lines)
             src/tokens/USDM.sol (74 lines)
             src/tokens/sUSDM.sol (330 lines)
Solidity:    0.8.27 (via_ir, optimizer 200 runs)
Chain:       HyperEVM (Hyperliquid L1)
```

---

## 3. Security Specification

### 3.1 Actors
```
User (untrusted): deposit, requestRedeem, claimRedeem, stake/unstake
Operator (semi-trusted): bridge, hedge, settle, distribute, fund/reclaim
Guardian (trusted): pause/unpause (dual: user + operator)
Governor (trusted, 24h timelock): set*, emergency*
Upgrader (trusted, 48h timelock): proxy upgrades
Hyperliquid L1 (external): spot/perp/HLP/BLP, precompile reads
```

### 3.2 Trust Model
```
Operator is the highest-risk actor:
  → Can bridge ALL netBridgeable USDC to L1
  → Can execute arbitrary hedges (within whitelist)
  → Can declare yield (bounded by 4 gates)
  → Can reclaim ALL USDC from RedeemEscrow (UNBOUNDED)
  → Cannot: mint/burn USDM, change config, upgrade, pause
```

### 3.3 Key Invariants
```
I1: totalBacking() >= usdm.totalSupply() (solvency)
I2: proposedYield <= distributableSurplus() (yield gate 3)
I3: proposedYield <= supply * bps * dt / (10000 * 365d) (yield gate 4)
I4: userShare + insuranceShare + foundationShare == totalYield
I5: RedeemRequest claimable only after cooldown
I6: lastSettlementTime monotonically increasing
```

---

## 4. Invariant Fuzzing

### 4.1 Scribble Annotations (TokenMath)
```
6 properties annotated + instrumented:
  P1: usdcEvmToL1Wei(x) == x * 100
  P2: usdcL1WeiToEvm(x) == x / 100
  P3: evmToL1Wei(x, 0) == x (identity)
  P4: l1WeiToEvm(x, 0) == x (identity)
  P5: spotNotional(0, *, *, *) == 0 (zero balance)
  P6: roundtripUsdc(x) <= x (floor rounding preserved)
```

### 4.2 Echidna Results
```
Mode: assertion
Fuzz campaigns: 50,229 calls
Coverage: 925 unique instructions
Result: ALL 7 PASSING (6 properties + AssertionFailed monitor)
Verdict: TokenMath is correct for all fuzzed inputs
```

### 4.3 Mythril Results
```
Target: TokenMathHarness (compiled bytecode)
Mode: symbolic execution
Result: No issues detected
Verdict: No overflow/underflow/logic errors in pure math
```

---

## 5. Findings

### 5.1 reclaimFromRedeemEscrow Has No Amount Bound — Major

```solidity
function reclaimFromRedeemEscrow(uint256 amount) external onlyOperator {
    require(amount > 0, "zero amount");
    IRedeemEscrow(redeemEscrow).reclaimTo(address(this), amount);
}
```

**Description:** The operator can reclaim ANY amount from RedeemEscrow,
including amounts exceeding the surplus. This can drain funds reserved for
pending redemptions, making user claims revert until re-funded.

**Impact:** If operator key is compromised, attacker can:
1. Reclaim all USDC from RedeemEscrow
2. Users cannot claimRedeem (escrow empty)
3. Bridge remaining vault USDC to L1
4. Total drain of EVM-side liquidity

**Mitigation:** Bound reclaim to `escrow.balance - totalObligations`:
```solidity
uint256 maxReclaim = IRedeemEscrow(redeemEscrow).reclaimable();
require(amount <= maxReclaim, "exceeds reclaimable");
```

**Status:** Requires operator compromise (semi-trusted role)

---

### 5.2 emergencyRawAction Sends Arbitrary Data to HyperCore — Major

```solidity
function emergencyRawAction(bytes calldata data) external onlyGovernor {
    ICoreWriter(HyperCoreConstants.CORE_WRITER).sendRawAction(data);
}
```

**Description:** Sends completely unvalidated bytes to HyperCore's raw action
writer. While gated by 24h timelock, a compromised Governor can execute
ANY HyperCore action (withdrawals, transfers, liquidations).

**Impact:** Full control over HyperCore L1 account.

**Mitigation:** Whitelist specific action types instead of raw passthrough.
Or require multi-sig confirmation for emergency actions.

**Status:** By design (escape hatch), but risk if Governor compromised.

---

### 5.3 USDM Not Burned Until claimRedeem — Medium

```
requestRedeem: USDM transferred to vault, obligation added
claimRedeem:   USDM burned, USDC paid from escrow
```

**Description:** Between request and claim, USDM totalSupply is unchanged
but the tokens are locked in the vault. The Accountant correctly subtracts
shortfall from distributableSurplus, preventing phantom yield. However,
the USDM sitting in the vault is not explicitly tracked as "pending burn"
in the vault's own accounting.

**Impact:** Low — Accountant handles it correctly via shortfall subtraction.
But if a future upgrade removes the shortfall check, yield could be inflated.

**Mitigation:** Track pendingBurnAmount in vault for defense-in-depth.

---

### 5.4 Yield Distribution Rounding Favors Foundation — Minor

```solidity
userShare = (totalYield * userYieldBps) / 10000;
insuranceShare = (totalYield * insuranceYieldBps) / 10000;
foundationShare = totalYield - userShare - insuranceShare;
```

**Description:** Foundation receives the remainder after floor-division.
Maximum dust per distribution: 2 wei (negligible).

**Impact:** Negligible. Not exploitable.

---

### 5.5 netBridgeable Excludes Pending Redemptions Correctly — Informational

```solidity
function netBridgeable() public view returns (uint256) {
    uint256 bal = usdc.balanceOf(address(this));
    uint256 sf = IRedeemEscrow(redeemEscrow).shortfall();
    uint256 reserved = sf + bridgeRetentionAmount;
    return bal > reserved ? bal - reserved : 0;
}
```

**Description:** Correctly subtracts shortfall + retention before bridging.
No issue found. Documented for completeness.

---

## 6. Limitations

```
1. HyperEVM precompiles (0x801, 0x807, 0x808, 0x811) could NOT be tested
   locally — they only exist on Hyperliquid L1. All L1 backing reads are
   UNVERIFIED in this audit.

2. ActionEncoder sends raw actions to HyperCore — the L1-side execution
   semantics are outside EVM scope and could not be verified.

3. MonetrixVault could not be compiled locally (via_ir + HyperEVM deps
   cause >5min compile). Scribble/Mythril were applied to TokenMath only.

4. sUSDM staking/unstaking flow was read but not fuzzed.

5. Cross-contract invariants (Vault ↔ Accountant ↔ Escrows) were analyzed
   manually but not formally verified.
```

---

## 7. CD Methodology Gaps (Honest Self-Assessment)

```
WHAT I DID (CD methodology):
  ✅ Step 0: Security Specification (actors, trust model, invariants)
  ✅ Step 1: Scribble annotations + instrumentation + Echidna fuzz
  ✅ Step 2: Mythril symbolic execution
  ✅ Step 3: State machine mapping + per-transition verification
  ✅ Step 4: Findings in CD report format
  ✅ Limitations section (honest about gaps)

WHAT I COULDN'T DO:
  ❌ Full-contract Scribble (MonetrixVault won't compile locally)
  ❌ Cross-contract invariant fuzzing (needs full system deployed)
  ❌ HyperEVM precompile testing (L1-only)
  ❌ Diligence Fuzzing SaaS (enterprise, not available)
  ❌ Formal verification (Certora/Halmos on full system)
  ❌ Fix review (no fix cycle to review)

WHAT I STILL NEED TO LEARN:
  1. Scribble advanced: stateful invariants, quantifiers, ghost variables
  2. Mythril advanced: multi-tx analysis, custom modules
  3. Certora Prover: formal spec language, CVL rules
  4. Cross-contract Echidna: multi-contract harnesses
  5. CD blog/research: Smart Contract Best Practices deep dive
  6. More report reading: need 5-10 more CD reports for pattern recognition
```

---

*BOZAGENTIC · CD Methodology Practice Complete*
*Scribble: ARMED + 50K fuzz PASS · Mythril: CLEAN · Manual: 2 Major + 1 Medium + 1 Minor*
