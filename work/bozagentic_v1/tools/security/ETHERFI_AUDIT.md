# ETHERFI — FULL FRAMEWORK AUDIT + CODE REFERENCE
# Liquid Restaking Protocol · 39K lines · UUPS Upgradeable
# BOZAGENTIC · 2026-07-30
# Source: github.com/etherfi-protocol/smart-contracts

---

## ARCHITECTURE

```
EtherFi: Liquid restaking on EigenLayer
  → Users deposit ETH → receive eETH (rebasing) or weETH (wrapped)
  → ETH staked on Ethereum + restaked on EigenLayer
  → Rewards flow back via oracle rebase

Core Contracts:
  LiquidityPool.sol (861 lines) — TVL accounting, deposit/withdraw, rebase
  EETH.sol (526 lines) — rebasing ERC20 (share-based)
  PriorityWithdrawalQueue.sol (746 lines) — fast withdrawal for whitelisted
  Liquifier.sol (578 lines) — deposit with stETH/ERC20
  EtherFiNodesManager.sol (607 lines) — validator management
  EtherFiOracle.sol (496 lines) — rebase oracle
  EtherFiAdmin.sol (635 lines) — admin operations
  WithdrawRequestNFT.sol (482 lines) — NFT-based withdrawal
  EtherFiRestaker.sol (519 lines) — EigenLayer restaking

Key Design:
  → UUPS upgradeable (all core contracts)
  → ReentrancyGuardTransient (EIP-1153, Solady)
  → Role-based access (RolesLibrary)
  → Rate limiting on mint/burn (IEtherFiRateLimiter)
  → Blacklister integration
  → PausableUntil (time-bounded pause)
```

---

## KEY PATTERNS (Learn from EtherFi)

### Pattern 1: Share-Based Rebasing Token (eETH)
```solidity
// eETH is NOT ERC4626. It's a share-based rebasing token (like Lido stETH).
// balanceOf(user) = shares[user] * TVL / totalShares

// Mint: LiquidityPool calculates shares, calls eETH.mintShares()
// Burn: LiquidityPool calls eETH.burnShares()
// Transfer: converts amount → shares internally

// Share conversion (LiquidityPool):
function _sharesForDepositAmount(uint256 _depositAmount) internal view returns (uint256) {
    uint256 totalPooledEther = getTotalPooledEther() - _depositAmount;
    if (totalPooledEther == 0) return _depositAmount;  // first deposit: 1:1
    return Math.mulDiv(_depositAmount, eETH.totalShares(), totalPooledEther, Math.Rounding.Down);
}

// WHY NO VIRTUAL SHARES:
// → eETH is NOT ERC4626 (no deposit/redeem on token itself)
// → Mint/burn ONLY via LiquidityPool (access controlled)
// → No permissionless "donate" function
// → TVL only changes via: deposit, withdraw, rebase (oracle-only)
// → Inflation attack IMPOSSIBLE (no way to inflate TVL without minting)
```

### Pattern 2: Rebase with Positive Cap
```solidity
// LiquidityPool.rebase() — oracle-driven TVL update
function rebase(int128 _accruedRewards, uint128 _protocolFees) external {
    if (msg.sender != address(etherFiAdminContract)) revert IncorrectCaller();
    
    // POSITIVE CAP: max 25 bps per rebase (~1 month at 3% APR)
    if (_accruedRewards > 0) {
        uint256 maxIncrease = (getTotalPooledEther() * MAX_POSITIVE_REBASE_BPS) / REBASE_BPS_DENOMINATOR;
        if (uint256(uint128(_accruedRewards)) > maxIncrease) revert RebaseExceedsPositiveCap();
    }
    // NEGATIVE: no cap here (oracle-side handles it)
    
    totalValueOutOfLp = uint128(int128(totalValueOutOfLp) + _accruedRewards);
}

// WHY: bounds a compromised oracle at the share-rate chokepoint
// Even if oracle is hacked, max +25 bps per rebase
// Negative rebase bounded by EtherFiAdmin (separate contract)
```

### Pattern 3: Snapshot + Verify (PriorityWithdrawalQueue)
```solidity
// EVERY operation follows this pattern:
function requestWithdraw(uint96 amountOfEEth, uint96 amountWithFee) external ... {
    // 1. SNAPSHOT before
    (uint256 lpEthBefore, uint256 queueEEthSharesBefore,) = _snapshotBalances();
    
    // 2. EXECUTE
    IERC20(address(eETH)).safeTransferFrom(msg.sender, address(this), amountOfEEth);
    (requestId,) = _queueWithdrawRequest(msg.sender, amountOfEEth, amountWithFee);
    
    // 3. VERIFY after
    _verifyRequestPostConditions(lpEthBefore, queueEEthSharesBefore, amountOfEEth);
}

// Post-condition:
function _verifyRequestPostConditions(...) internal view {
    uint256 expectedSharesReceived = liquidityPool.sharesForAmount(amountOfEEth);
    if (eETH.shares(address(this)) != queueEEthSharesBefore + expectedSharesReceived) 
        revert UnexpectedBalanceChange();
    if (liquidityPool.totalValueInLp() != lpEthBefore) 
        revert UnexpectedBalanceChange();
}

// WHY: defense-in-depth
// Even if internal logic has a bug, post-conditions catch it
// Catches: unexpected minting, unexpected TVL changes, share manipulation
```

### Pattern 4: Dual Reentrancy Guard
```solidity
// EtherFi uses BOTH:
// 1. DeprecatedOZReentrancyGuard (storage-based, for upgrade compatibility)
// 2. ReentrancyGuardTransient (EIP-1153, gas-efficient)

contract PriorityWithdrawalQueue is 
    DeprecatedOZReentrancyGuard,  // old guard (storage slot preserved for upgrades)
    ReentrancyGuardTransient,     // new guard (transient storage, 100 gas)
    ...

// WHY BOTH:
// → Upgraded from old OZ guard → can't remove storage slot
// → Added transient guard for gas savings
// → Belt and suspenders
```

### Pattern 5: nonDecreasingRate Modifier
```solidity
// Prevents share rate from decreasing during an operation
modifier nonDecreasingRate() {
    (uint256 P0, uint256 S0) = _snapRate();  // TVL, shares BEFORE
    _;
    _checkRateNonDec(P0, S0);  // verify rate didn't drop
}

function _checkRateNonDec(uint256 P0, uint256 S0) internal view {
    (uint256 P1, uint256 S1) = _snapRate();
    if (S0 != 0 && S1 != 0 && P1 * S0 < P0 * S1) revert EETHRateDeflation();
}

// WHY: prevents operations that would dilute existing holders
// Applied to: deposit, withdraw, burnEEthShares, burnEEthSharesForNonETHWithdrawal
// NOT applied to: claim path (withdraw(uint256,uint256)) — intentional
```

### Pattern 6: Escrow Segregation
```solidity
// Withdrawal ETH is segregated from LP:
// LP.totalValueInLp → LP sends ETH → WRNFT/PWQ holds it
// TVL preserved: totalValueInLp -= amount, totalValueOutOfLp += amount

function _lockEth(address _dest, uint128 _amount) internal {
    if (!escrowMigrationCompleted) revert MigrationNotComplete();
    if (totalValueInLp < _amount) revert InsufficientLiquidity();
    totalValueInLp    -= _amount;
    totalValueOutOfLp += _amount;
    _sendFund(_dest, _amount);
    _checkTotalValueInLp();
}

// WHY: prevents withdrawal ETH from being used for new deposits
// Clear separation: LP holds staking ETH, WRNFT/PWQ holds withdrawal ETH
```

---

## AUDIT FINDINGS

### Finding 1: Claim Path Missing nonDecreasingRate (LOW)
```solidity
// LiquidityPool.withdraw(uint256 _amount, uint256 _share)
// Called by WRNFT/PWQ at claim time
function withdraw(uint256 _amount, uint256 _share) external nonReentrant {
    // NO nonDecreasingRate modifier!
    // NO whenNotPaused!
    totalValueOutOfLp -= uint128(_amount);
    eETH.burnShares(msg.sender, _share);
}

// _share is snapshotted at REQUEST time (old rate)
// If negative rebase happened between request and claim:
//   → _share is worth LESS than _amount at current rate
//   → Burning _share removes less value than _amount
//   → Rate DECREASES for remaining holders

// MITIGATION:
// → Negative rebase bounded by EtherFiAdmin (oracle-side cap)
// → If totalValueOutOfLp < _amount → underflow revert (claim DoS)
// → Comment acknowledges: "finalized-withdrawal DoS, bounded by rebase-APR cap"

// SEVERITY: LOW
// → Rate decrease bounded by oracle cap
// → Worst case: claim reverts (DoS), not fund loss
// → By design: claims must work even during pause
```

### Finding 2: User-Specified Fee in PriorityWithdrawalQueue (INFO)
```solidity
function requestWithdraw(uint96 amountOfEEth, uint96 amountWithFee) external ... {
    if (amountWithFee == 0 || amountWithFee > amountOfEEth) revert InvalidAmount();
    // amountWithFee can == amountOfEEth → ZERO FEE
}

// User specifies their own fee (amountOfEEth - amountWithFee)
// No minimum fee enforcement
// Fee stays in queue contract (not sent to treasury)

// MITIGATION: whitelisted-only (isWhitelisted check)
// → Only trusted users can access priority queue
// → Fee is likely negotiated off-chain or set by frontend

// SEVERITY: INFO (by design for whitelisted users)
```

### Finding 3: receive() Allows Anyone to Rebalance LP Accounting (INFO)
```solidity
// LiquidityPool.receive()
receive() external payable {
    if (msg.value > type(uint128).max) revert InvalidAmount();
    totalValueOutOfLp -= uint128(msg.value);  // can underflow → revert
    totalValueInLp += uint128(msg.value);
    _checkTotalValueInLp();
}

// Anyone can send ETH to LP
// Effect: moves value from OutOfLp → InLp
// TVL unchanged (InLp + OutOfLp = same)
// Share price unchanged
// But: totalValueOutOfLp decreases (could affect withdrawal capacity)

// MITIGATION:
// → Underflow protection (Solidity 0.8)
// → Can only send up to totalValueOutOfLp
// → _checkTotalValueInLp ensures InLp <= balance
// → No economic impact (TVL preserved)

// SEVERITY: INFO (no economic impact, just accounting rebalance)
```

### Finding 4: Liquifier balanceOf Measurement at etherfiRestaker (INFO)
```solidity
// For non-L2 tokens:
uint256 balanceBefore = IERC20(_token).balanceOf(address(etherfiRestaker));
IERC20(_token).safeTransferFrom(msg.sender, address(etherfiRestaker), _amount);
amountReceived = IERC20(_token).balanceOf(address(etherfiRestaker)) - balanceBefore;

// Measures balance at etherfiRestaker, not Liquifier
// If etherfiRestaker has hooks that modify token balance → wrong measurement
// But: nonReentrant prevents re-entry, single tx atomicity

// SEVERITY: INFO (safe due to nonReentrant + atomicity)
```

### Finding 5: PriorityWithdrawalQueue — No Rate Check on Cancel of Finalized Request (INFO)
```solidity
function cancelWithdraw(WithdrawRequest calldata request) external ... {
    bool wasFinalized = _finalizedRequests.contains(reqId);
    uint256 expectedLpEthDelta = wasFinalized ? uint256(request.amountOfEEth) : 0;
    requestId = _cancelWithdrawRequest(request);
    _verifyCancelPostConditions(lpEthBefore, queueEEthSharesBefore, userEEthSharesBefore, request.user, expectedLpEthDelta);
}

// Canceling a FINALIZED request returns ETH to LP
// Shares returned to user at CURRENT rate (not request-time rate)
// If rate increased: user gets MORE eETH than they deposited
// → This is a GAIN for the user, not a loss
// → LP rate unaffected (ETH returned + shares returned)

// SEVERITY: INFO (user benefits from rate increase on cancel)
```

### Finding 6: MAX_POSITIVE_REBASE_BPS = 25 bps Hardcoded (INFO)
```solidity
uint256 public constant MAX_POSITIVE_REBASE_BPS = 25;
// 25 bps ≈ 1 month of reward accrual at 3% APR
// NOT governance-configurable (hardcoded constant)

// If ETH staking APR increases significantly (>3% APR):
// → Legitimate rewards could exceed 25 bps per rebase
// → Oracle would need multiple rebases to catch up
// → Not a security issue, just operational constraint

// SEVERITY: INFO (conservative safety bound)
```

---

## COMPARISON: ETHERFI vs AAVE vs MORPHO vs ARCADIA

```
                    EtherFi         Aave V3.1       Morpho          Arcadia V2
Type:               LST/LRT         Lending         Lending         Lending
Token:              Rebasing        aToken          N/A             ERC4626
                    (share-based)   (rebasing)                      (VAS=0)
                    
TVL accounting:     stored ✅       virtualBal ✅   stored ✅       balanceOf ❌
Inflation attack:   impossible      impossible      impossible      possible ❌
                    (no donate fn)  (no donate fn)  (no donate fn)  (donateToTranche)
                    
Upgrade:            UUPS ✅         Proxy ✅        None ✅         None ✅
Reentrancy:         Transient+OZ    None (optimistic) None (optimistic) None ⚠️
Rate protection:    nonDecRate ✅   N/A             N/A             N/A
Rebase cap:         25 bps ✅       N/A             N/A             N/A
Withdrawal:         NFT + Queue     instant         instant         instant
Bad debt:           N/A (no borrow) deficit+Umbrella per-market     tranche cascade

Bug found:          0 exploitable   0 exploitable   0 exploitable   1 MEDIUM ✅
Code quality:       ⭐⭐⭐⭐          ⭐⭐⭐⭐⭐         ⭐⭐⭐⭐⭐         ⭐⭐⭐
Audit history:      multiple        ToB+C4+Zellic   ToB+Spearbit    few
```

---

## WHAT TO STEAL FROM ETHERFI

```
1. Snapshot + Verify pattern
   → Before: snapshot balances
   → Execute operation
   → After: verify post-conditions
   → Catches bugs that unit tests miss
   → Defense-in-depth at the contract level

2. nonDecreasingRate modifier
   → Prevents any operation from diluting existing holders
   → Simple: P1*S0 >= P0*S1
   → Apply to ALL state-changing functions

3. Rebase cap (MAX_POSITIVE_REBASE_BPS)
   → Bounds oracle damage at the share-rate chokepoint
   → Even if oracle is compromised, max +25 bps per call
   → Hardcoded (not governance-configurable) = stronger guarantee

4. Escrow segregation
   → Withdrawal ETH separated from staking ETH
   → totalValueInLp vs totalValueOutOfLp
   → Prevents withdrawal funds from being re-used

5. Dual reentrancy guard (upgrade-safe)
   → Keep old storage slot (upgrade compatibility)
   → Add transient guard (gas savings)
   → Belt and suspenders for upgradeable contracts

6. Rate limiting on mint/burn
   → Global bucket per operation type
   → Bounds damage from compromised mint path
   → Transfers NOT rate-limited (don't change supply)
```

---

## HONEST ASSESSMENT

```
EtherFi: 0 exploitable bugs found
  → Well-designed with multiple defense layers
  → Snapshot+verify catches internal bugs
  → nonDecreasingRate prevents dilution
  → Rebase cap bounds oracle damage
  → Escrow segregation prevents fund mixing

BUT: more complex than Morpho (39K vs 555 lines)
  → More surface area for future bugs
  → UUPS upgradeable = upgrade risk
  → Multiple contracts interacting = composability risk
  → Newer code (less battle-tested than Aave)

WHERE BUGS MIGHT HID:
  → EtherFiRestaker (EigenLayer interactions)
  → EtherFiOracle (rebase logic, validator accounting)
  → Cross-chain weETH (L2 minting)
  → New integrations (Pendle, Curve, etc.)
  → Upgrade transactions (storage layout changes)
  → WithdrawRequestNFT (482 lines, not fully read)
```

---

*BOZAGENTIC · "EtherFi: defensive architecture done right. Snapshot+verify is the pattern to steal."*
