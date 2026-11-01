# MONETRIX — SECURITY SPECIFICATION (CD Methodology)
# Consensys Diligence Step 0: Define BEFORE reading code
# BOZAGENTIC · 2026-07-30

---

## 4.1 ACTORS

```
USER (untrusted):
  → deposit(USDC) → receive USDM (1:1)
  → requestRedeem(USDM) → queue with cooldown
  → claimRedeem(requestId) → receive USDC from RedeemEscrow
  → stake USDM → sUSDM (yield-bearing)
  → unstake sUSDM → USDM (with cooldown)

OPERATOR (semi-trusted, delay=0):
  → keeperBridge: send USDC to L1 (Hyperliquid)
  → bridgePrincipalFromL1: bring USDC back for redemptions
  → bridgeYieldFromL1: bring yield back
  → executeHedge / closeHedge / repairHedge: delta-neutral hedging
  → depositToHLP / withdrawFromHLP: HLP vault management
  → supplyToBlp / withdrawFromBlp: BLP management
  → settle(proposedYield): declare daily yield
  → distributeYield: split yield to users/insurance/foundation
  → fundRedemptions: move USDC to RedeemEscrow
  → reclaimFromRedeemEscrow: reclaim excess from escrow

GUARDIAN (trusted, delay=0):
  → pause / unpause (user operations)
  → pauseOperator / unpauseOperator (operator operations)

GOVERNOR (trusted, 24h timelock):
  → set* parameters (config, accountant, escrows, etc.)
  → emergencyRawAction (escape hatch to HyperCore)
  → emergencyBridgePrincipalFromL1

UPGRADER (trusted, 48h timelock):
  → _authorizeUpgrade (proxy upgrades)

HYPERLIQUID L1 (external, trusted infrastructure):
  → Spot trading, perp trading, HLP vault, BLP
  → Precompile reads (0x801, 0x807, 0x808, 0x811)
  → Bridge (SEND_ASSET action)
```

## 4.2 TRUST MODEL

```
FULLY TRUSTED:
  → Governor (24h timelock mitigates)
  → Guardian (pause only, no fund movement)
  → Hyperliquid L1 (infrastructure)
  → USDC token (standard ERC20)

SEMI-TRUSTED (can affect funds, but bounded):
  → Operator:
    → Can bridge USDC to L1 (bounded by netBridgeable)
    → Can execute hedges (bounded by whitelist)
    → Can declare yield (bounded by 4 gates in Accountant)
    → Can fund/reclaim escrow (bounded by shortfall)
    → CANNOT: mint USDM, change config, upgrade, pause

UNTRUSTED:
  → User: can only deposit/redeem/stake within bounds
  → External callers: all state-changing functions gated
```

## 4.3 SECURITY PROPERTIES (INVARIANTS)

### Solvency Invariants:
```
I1: totalBacking() >= usdm.totalSupply()
    → All USDM is backed by real assets (USDC + L1 positions)
    → MUST hold at ALL times

I2: distributableSurplus() >= 0 before any yield distribution
    → Can't distribute yield that doesn't exist

I3: outstandingL1Principal tracks actual L1 principal
    → No phantom principal (bridged but not tracked)

I4: RedeemEscrow.balance >= total pending redemptions
    → All queued redemptions are fundable
```

### Yield Invariants:
```
I5: proposedYield <= distributableSurplus()
    → Gate 3 in Accountant.settleDailyPnL

I6: proposedYield <= supply * maxAnnualYieldBps * elapsed / (10000 * 365d)
    → Gate 4: annualized APR cap (max 15%)

I7: userShare + insuranceShare + foundationShare == totalYield
    → Yield split is exact (no leakage)

I8: If susdm.totalSupply() == 0, userShare = 0
    → Empty vault yield goes to foundation (not captured by next depositor)
```

### Access Control Invariants:
```
I9: USDM.mint only callable by Vault
    → No unauthorized minting

I10: USDM.burn only callable by Vault
    → No unauthorized burning

I11: All operator functions require !operatorPaused
    → Guardian can halt all operator actions

I12: All user functions require !paused
    → Guardian can halt all user actions

I13: Governor actions require 24h timelock
    → No instant parameter changes
```

### Lifecycle Invariants:
```
I14: RedeemRequest.cooldownEnd > block.timestamp at creation
    → Cooldown is always in the future

I15: claimRedeem deletes request (no double-claim)
    → Request can only be claimed once

I16: lastSettlementTime monotonically increasing
    → No time-travel in settlement

I17: minSettlementInterval >= 1 hour (config bounded)
    → Can't settle more than once per hour
```

---

## STATE MACHINE

### USDM Lifecycle:
```
                    deposit()
  [No USDM] ──────────────────→ [USDM held by user]
                                      │
                    requestRedeem()    │  stake()
                    ┌──────────────────┤──────────┐
                    ▼                  │          ▼
            [USDM in Vault    [USDM held]   [sUSDM held]
             redeem queue]        │          │
                    │             │  unstake()│
                    │ claimRedeem │◄──────────┘
                    ▼             │
            [USDM burned]    [USDM held]
            [USDC paid from
             RedeemEscrow]
```

### USDC Flow:
```
  [User USDC] ──deposit()──→ [Vault USDC]
                                  │
                    keeperBridge()│
                                  ▼
                           [L1 Hyperliquid]
                           (spot/perp/HLP/BLP)
                                  │
              bridgePrincipalFromL1() / bridgeYieldFromL1()
                                  │
                                  ▼
                           [Vault USDC]
                           ┌──────┼──────┐
                           │      │      │
              fundRedemptions()  settle() │
                           │      │      │
                           ▼      ▼      ▼
                    [RedeemEscrow] [YieldEscrow] [Vault]
                           │      │
              claimRedeem()│  distributeYield()
                           │      │
                           ▼      ▼
                    [User USDC]  [sUSDM yield / Insurance / Foundation]
```

### Settlement Lifecycle:
```
  [Uninitialized] ──initializeSettlement()──→ [Active]
                                                  │
                                    settleDailyPnL()
                                    (4 gates check)
                                                  │
                                                  ▼
                                          [Yield declared]
                                                  │
                                        distributeYield()
                                                  │
                                          ┌───────┼───────┐
                                          ▼       ▼       ▼
                                    [sUSDM]  [Insurance] [Foundation]
```

---

## PER-TRANSITION VERIFICATION CHECKLIST

### deposit():
```
✅ USDC transferred FROM user TO vault (safeTransferFrom)
✅ USDM minted TO user (1:1)
✅ Amount bounds checked (min/max/TVL cap)
✅ nonReentrant + whenNotPaused
⚠️ No slippage check (1:1 mint, acceptable for stablecoin)
```

### requestRedeem():
```
✅ USDM transferred FROM user TO vault
✅ RedeemEscrow.addObligation(usdmAmount) — tracks liability
✅ Cooldown set (block.timestamp + redeemCooldown)
✅ Request stored with owner + amount + cooldownEnd
⚠️ USDM sits in vault until claim — not burned yet
⚠️ addObligation increases shortfall — affects netBridgeable
```

### claimRedeem():
```
✅ Cooldown enforced (block.timestamp >= cooldownEnd)
✅ Owner check (msg.sender == req.owner)
✅ Request deleted (no double-claim)
✅ USDM burned (from vault balance)
✅ RedeemEscrow.payOut(msg.sender, amount) — USDC to user
⚠️ payOut requires escrow has sufficient USDC
⚠️ If escrow underfunded → claim reverts (user stuck until funded)
```

### keeperBridge():
```
✅ Interval check (lastBridgeTimestamp + bridgeInterval)
✅ Amount = netBridgeable() (balance - shortfall - retention)
✅ outstandingL1Principal += amount (tracking)
✅ USDC approved + deposited to coreDepositWallet
⚠️ Bridge to L1 is ASYNC — USDC leaves EVM, arrives on L1 later
⚠️ During transit: USDC not in vault, not on L1 yet
```

### settle():
```
✅ proposedYield > 0
✅ vaultBal - shortfall >= proposedYield (EVM USDC sufficiency)
✅ Accountant.settleDailyPnL(proposedYield) — 4 gates
✅ USDC transferred to YieldEscrow
⚠️ proposedYield is OPERATOR-ASSERTED (off-chain computed)
⚠️ Bounded by gates, but operator chooses the value
```

### distributeYield():
```
✅ totalYield from YieldEscrow.balance()
✅ USDC pulled from YieldEscrow to Vault
✅ Balance check (balBefore + totalYield)
✅ Split: user/insurance/foundation (bps-based)
✅ Empty vault check (susdm.totalSupply() == 0 → userShare = 0)
✅ USDM minted for userShare → injected into sUSDM
✅ Insurance USDC → InsuranceFund
✅ Foundation USDC → foundation address
⚠️ foundationShare = totalYield - userShare - insuranceShare (remainder)
⚠️ Rounding: userShare + insuranceShare might not exactly divide
    → foundationShare absorbs rounding (favors foundation slightly)
```

---

## POTENTIAL FINDINGS (to verify with tools)

### F1: USDM not burned until claimRedeem (MEDIUM?)
```
requestRedeem: USDM transferred to vault, obligation added
claimRedeem: USDM burned, USDC paid

Between request and claim:
  → USDM still exists (totalSupply unchanged)
  → But obligation tracked in RedeemEscrow
  → Accountant.distributableSurplus subtracts shortfall
  → So yield is correctly bounded

Question: Can user requestRedeem, then transfer remaining USDM
to another address, and that address also interacts with protocol?
→ Yes, but each user's USDM is independent
→ No double-spend because USDM was transferred to vault
```

### F2: emergencyRawAction bypasses ALL checks (BY DESIGN?)
```
emergencyRawAction(bytes calldata data) external onlyGovernor {
    ICoreWriter(HyperCoreConstants.CORE_WRITER).sendRawAction(data);
}

→ Sends ARBITRARY data to HyperCore
→ No validation of `data` content
→ Only gated by 24h timelock (Governor)
→ Comment says: "DO NOT check either pause flag"

Risk: If Governor key compromised → arbitrary HyperCore action
Mitigation: 24h timelock gives time to react
CD would flag: "Critical if Governor is single EOA"
```

### F3: Operator can reclaim from RedeemEscrow (MEDIUM?)
```
reclaimFromRedeemEscrow(amount) external onlyOperator {
    IRedeemEscrow(redeemEscrow).reclaimTo(address(this), amount);
}

→ No bounds check on `amount`!
→ Operator can reclaim ALL USDC from RedeemEscrow
→ Pending redemptions become unfundable
→ Users can't claim until re-funded

BUT: Operator is semi-trusted
CD would ask: "Is this bounded by shortfall?"
Answer: NO — reclaimTo has no on-chain bound
```

### F4: Yield distribution rounding (LOW)
```
userShare = (totalYield * userYieldBps) / 10000
insuranceShare = (totalYield * insuranceYieldBps) / 10000
foundationShare = totalYield - userShare - insuranceShare

→ Foundation gets remainder (rounding dust)
→ Max dust per distribution: 2 wei (negligible)
→ Not exploitable
```

### F5: netBridgeable doesn't account for pending deposits (INFO)
```
netBridgeable = balance - shortfall - bridgeRetentionAmount

→ Pending deposits (totalPendingDepositAssets) NOT subtracted
→ But Monetrix doesn't have pending deposits (instant mint)
→ So this is N/A for current design
```
