# AAVE V3 — CODE REFERENCE + AUDIT FINDINGS
# Belajar pattern + cari bug sekaligus
# BOZAGENTIC · 2026-07-30
# Source: github.com/aave-dao/aave-v3-origin (21K lines)

---

## PART 1: ARCHITECTURE (vs Morpho vs Arcadia)

```
Aave V3:
  Pool.sol (941 lines) — abstract, behind proxy
  ├── SupplyLogic.sol (337 lines)
  ├── BorrowLogic.sol (224 lines)
  ├── LiquidationLogic.sol (679 lines)
  ├── FlashLoanLogic.sol (253 lines)
  ├── ReserveLogic.sol (275 lines) — interest + indexes
  ├── ValidationLogic.sol (550 lines)
  ├── GenericLogic.sol (258 lines) — health factor
  ├── PoolConfigurator.sol (622 lines) — admin
  ├── AToken.sol (338 lines) — rebasing supply token
  ├── VariableDebtToken.sol — debt token
  └── Extensions:
      ├── ERC4626StataTokenUpgradeable.sol (311 lines) ← NEWEST, least audited
      └── ERC20AaveLMUpgradeable.sol (309 lines)

COMPARISON:
  Morpho:  555 lines, 1 contract, no proxy, no inheritance
  Arcadia: 1338 lines, 1 contract, no proxy, inheritance
  Aave V3: 21K lines, 15+ contracts, proxy, libraries, extensions
  
  → Aave is the MOST COMPLEX = largest attack surface
  → But also MOST AUDITED (ToB, Certora, Zellic, multiple C4 contests)
  → Bug hunting: focus on EXTENSIONS (Stata token, LM token)
```

---

## PART 2: KEY PATTERNS (Learn from Aave)

### Pattern 1: Virtual Underlying Balance (Stored Accounting)
```solidity
// Aave V3.1: virtualUnderlyingBalance (like Morpho!)
reserve.virtualUnderlyingBalance -= amount.toUint128();  // flash loan
reserve.virtualUnderlyingBalance += liquidityAdded.toUint128();  // supply
reserve.virtualUnderlyingBalance -= liquidityTaken.toUint128();  // withdraw

// NOT balanceOf() — stored accounting
// → Immune to donation attacks
// → Same pattern as Morpho, DIFFERENT from Arcadia/Basin

// LESSON: Aave learned from Basin/Arcadia bugs
// V3.0 used balanceOf() in some places
// V3.1 switched to virtualUnderlyingBalance
```

### Pattern 2: Cache-Update-Validate Pattern
```solidity
// Aave's standard flow for every operation:
// 1. cache() — read all storage into memory (1 SLOAD per variable)
// 2. updateState() — accrue interest, update indexes
// 3. validate() — check health, caps, active status
// 4. execute() — modify state
// 5. updateRates() — recalculate interest rates

// WHY: minimizes SLOADs (gas), ensures consistent state
// ReserveCache struct holds ALL reserve data in memory
// Only writes back to storage at the end

DataTypes.ReserveCache memory reserveCache = reserve.cache();
reserve.updateState(reserveCache);
// ... validation + execution ...
reserve.updateInterestRatesAndVirtualBalance(reserveCache, ...);
```

### Pattern 3: Rate-Based ERC4626 (Stata Token)
```solidity
// Stata token: ERC4626 wrapper for aTokens
// Conversion is RATE-BASED, not balance-based:

function _convertToShares(uint256 assets, Math.Rounding rounding)
    internal view override returns (uint256) {
    return assets.mulDiv(RAY, _rate(), rounding);
    // shares = assets * 1e27 / liquidityIndex
}

function _convertToAssets(uint256 shares, Math.Rounding rounding)
    internal view override returns (uint256) {
    return shares.mulDiv(_rate(), RAY, rounding);
    // assets = shares * liquidityIndex / 1e27
}

function _rate() internal view returns (uint256) {
    return POOL.getReserveNormalizedIncome(asset());
    // Global Aave liquidity index (monotonically increasing)
}

// WHY THIS IS SAFE:
// → Rate is GLOBAL (per Aave reserve), not per-vault
// → Can't manipulate rate by donating to Stata token
// → Direct aToken donation = stuck (doesn't affect rate)
// → Inflation attack IMPOSSIBLE by design

// COMPARISON:
// OZ ERC4626:    shares = assets * totalShares / totalAssets  (balance-based)
// Morpho:        shares = assets * (totalShares + 1e6) / (totalAssets + 1)  (balance-based + virtual)
// Arcadia:       shares = assets * (supply + VAS) / (assets + VAS)  (balance-based, VAS=0 = BUG)
// Aave Stata:    shares = assets * RAY / rate  (rate-based = IMMUNE)
```

### Pattern 4: Flash Loan Flow (Anti-Reentrancy)
```solidity
// Aave flash loan order:
// 1. validate (before any state change)
// 2. virtualUnderlyingBalance -= amount (accounting)
// 3. transferUnderlyingTo (send tokens)
// 4. receiver.executeOperation (callback)
// 5. _handleFlashLoanRepayment (pull tokens back + premium)

// KEY: validation BEFORE callback
// → Prevents rate manipulation during callback
// → Comment: "altered to protect against reentrance and rate manipulation"

// vs Morpho:
// Morpho: state update → callback → transferFrom
// Aave:   validate → transfer → callback → repayment
// Both safe, different approaches
```

### Pattern 5: Deficit System (V3.1 — Bad Debt)
```solidity
// New in V3.1: Umbrella contract covers bad debt
reserve.deficit += badDebtAmount;  // track per-reserve

// executeEliminateDeficit:
// → Umbrella calls this
// → Burns caller's aTokens to cover deficit
// → reserve.deficit -= amount
// → Requires: caller has no debt, reserve is active

// vs Arcadia:
// Arcadia: _processDefault cascades through tranches (can brick pool)
// Aave: deficit tracked per-reserve, Umbrella covers it
// → No cascade, no bricking
// → Socialized loss via Umbrella stakers
```

### Pattern 6: try/catch Permit (Silent Failure)
```solidity
// Aave supplyWithPermit:
try IERC20WithPermit(asset).permit(
    _msgSender(), address(this), amount, deadline, permitV, permitR, permitS
) {} catch {}

// Permit failure SILENTLY caught
// → If permit fails, safeTransferFrom will also fail (no allowance)
// → UNLESS user has pre-existing allowance
// → By design: permit is optional convenience

// ⚠️ PATTERN TO WATCH:
// → try/catch can hide real errors
// → If permit succeeds but with wrong params → silent wrong approval
// → But: subsequent transferFrom validates the actual allowance
```

---

## PART 3: AUDIT FINDINGS

### Finding 1: Stata Token — depositATokens Balance Cap Race (INFO)
```solidity
function depositATokens(uint256 assets, address receiver) external returns (uint256) {
    uint256 actualUserBalance = IERC20(aToken()).balanceOf(_msgSender());
    if (assets > actualUserBalance) {
        assets = actualUserBalance;  // cap to actual balance
    }
    uint256 shares = previewDeposit(assets);
    _deposit(_msgSender(), receiver, assets, shares, false);
}

// aTokens REBASE (balance grows with interest)
// Between balanceOf() and safeTransferFrom(), balance could grow
// → User specifies 100 aTokens, has 100 at check time
// → By transfer time, has 100.001 (interest accrued)
// → Only 100 transferred (capped amount)
// → 0.001 stays with user (not lost, just not deposited)

// SEVERITY: INFO — no loss, just minor UX inconsistency
// The cap is a FEATURE (handles rebasing during tx mining)
```

### Finding 2: Stata Token — No Virtual Shares But Rate-Based (INFO)
```solidity
// Stata token does NOT use OZ virtual shares
// _convertToShares uses rate, not totalAssets/totalSupply
// → Inflation attack via donation: IMPOSSIBLE (rate is global)
// → But: if Aave's liquidityIndex somehow resets or manipulates...
//   → liquidityIndex is monotonically increasing (never decreases)
//   → Only increases via interest accrual
//   → No admin function to decrease it
//   → SAFE

// SEVERITY: INFO — rate-based conversion is inherently safe
// No virtual shares needed because the attack vector doesn't exist
```

### Finding 3: Stata Token — maxRedeem Uses Pool Virtual Balance (LOW)
```solidity
function maxRedeem(address owner) public view override returns (uint256) {
    // ...
    uint128 virtualUnderlyingBalance = POOL.getVirtualUnderlyingBalance(asset());
    uint256 underlyingTokenBalanceInShares = convertToShares(virtualUnderlyingBalance);
    uint256 cachedUserBalance = balanceOf(owner);
    return underlyingTokenBalanceInShares >= cachedUserBalance
        ? cachedUserBalance
        : underlyingTokenBalanceInShares;
}

// maxRedeem limited by Aave pool's available liquidity
// If pool is fully utilized (all supplied assets borrowed):
//   → virtualUnderlyingBalance ≈ 0
//   → maxRedeem ≈ 0
//   → User can't redeem even though they have shares

// This is BY DESIGN (can't withdraw what's borrowed)
// But: Stata token holders might not expect this
// → They hold an ERC4626 token that sometimes can't be redeemed
// → Integration risk: protocols that assume maxRedeem > 0

// SEVERITY: LOW — by design, but integration risk
```

### Finding 4: Flash Loan — virtualUnderlyingBalance Underflow Check (INFO)
```solidity
// FlashLoanLogic:
reservesData[params.assets[i]].virtualUnderlyingBalance -= vars.currentAmount.toUint128();

// No explicit check that virtualUnderlyingBalance >= currentAmount
// BUT: ValidationLogic.validateFlashloan checks:
//   → amount <= available liquidity
//   → available = virtualUnderlyingBalance (in V3.1)
// So underflow is prevented by validation

// SEVERITY: INFO — validation prevents underflow
// But: if validation logic changes, this becomes critical
// Defense in depth: add explicit check at subtraction point
```

### Finding 5: LiquidationLogic — executeEliminateDeficit (INFO)
```solidity
// New V3.1 function: Umbrella covers bad debt
function executeEliminateDeficit(...) external returns (uint256) {
    require(params.amount != 0, Errors.InvalidAmount());
    require(currentDeficit != 0, Errors.ReserveNotInDeficit());
    require(!userConfig.isBorrowingAny(), Errors.UserCannotHaveDebt());
    // ...
    IAToken(reserveCache.aTokenAddress).burn({
        from: params.user,
        receiverOfUnderlying: reserveCache.aTokenAddress,
        amount: balanceWriteOff,
        scaledAmount: scaledBalanceWriteOff,
        index: reserveCache.nextLiquidityIndex
    });
    reserve.deficit -= balanceWriteOff.toUint128();
}

// ONLY callable by Umbrella (onlyUmbrella modifier on Pool)
// Burns Umbrella's aTokens to cover deficit
// → Umbrella stakers lose their aTokens
// → Deficit reduced
// → No cascade to other reserves

// SEVERITY: INFO — well-designed bad debt mechanism
// Better than Arcadia's tranche cascade (no bricking)
```

### Finding 6: Pool — supplyWithPermit Silent Catch (INFO)
```solidity
try IERC20WithPermit(asset).permit(...) {} catch {}
SupplyLogic.executeSupply(...);

// If permit fails silently:
// → executeSupply calls safeTransferFrom
// → If no allowance → revert (tx fails)
// → If pre-existing allowance → succeeds (permit was unnecessary)

// No security issue: the transferFrom is the real validation
// Permit is just a gas-saving convenience

// SEVERITY: INFO
```

---

## PART 4: AAVE vs MORPHO vs ARCADIA — PATTERN COMPARISON

```
                    Aave V3.1         Morpho Blue       Arcadia V2
Accounting:         virtualBalance    stored            balanceOf ❌
                    (stored) ✅       ✅                
                    
ERC4626:            Stata (rate-based) N/A              Tranche (VAS=0) ❌
                    immune ✅                           vulnerable
                    
Inflation attack:   impossible        impossible        possible ❌
                    (rate-based)      (no donate fn)    (donateToTranche)
                    
Bad debt:           deficit + Umbrella per-market       tranche cascade ❌
                    (no cascade) ✅   (isolated) ✅     (can brick pool)
                    
Flash loan:         validate→send→    send→callback→    N/A
                    callback→repay    repay             
                    ✅                ✅                
                    
Reentrancy:         validation before optimistic        CEI
                    callback ✅       accounting ✅     (partial) ⚠️
                    
Code size:          21K lines         555 lines         1338 lines
Audit history:      ToB+C4+Zellic+    ToB+Spearbit+     few
                    Certora+multiple  Zellic+multiple   
                    
Bug found:          0 exploitable     0 exploitable     1 MEDIUM ✅
```

---

## PART 5: WHAT TO STEAL FROM AAVE

```
1. Cache pattern — read all storage once, work in memory
   → Saves 50%+ gas on multi-variable operations
   → ReserveCache struct = single source of truth during operation

2. Rate-based ERC4626 — immune to inflation attacks
   → Don't use totalAssets/totalSupply for conversion
   → Use a monotonically increasing rate (liquidity index)
   → Donation can't affect rate → no inflation attack

3. virtualUnderlyingBalance — stored accounting
   → Track token flows explicitly
   → Never derive from balanceOf()
   → Update on every supply/withdraw/borrow/repay/flashloan

4. Deficit system — clean bad debt handling
   → Track per-reserve
   → External backstop (Umbrella) covers it
   → No cascade, no bricking

5. Validation-before-callback — anti-reentrancy
   → Validate ALL conditions before external calls
   → State changes after validation
   → Callback last (or with payment requirement)

6. try/catch for permit — graceful degradation
   → Permit is convenience, not security
   → Real validation happens at transferFrom
   → Don't let permit failure block the operation
```

---

## PART 6: HONEST ASSESSMENT

```
Aave V3 core: NO exploitable bugs found
  → 21K lines, audited by 5+ firms, battle-tested 3+ years
  → V3.1 fixed the balanceOf() issues (learned from Basin/Arcadia)
  → virtualUnderlyingBalance = stored accounting (like Morpho)

Stata token (extension): NO exploitable bugs found
  → Rate-based ERC4626 = immune to inflation
  → Newer code (less audited) but well-designed
  → 6 INFO/LOW findings, none exploitable

WHERE BUGS MIGHT HID:
  → New Aave extensions (GHO, Lido, EtherFi integrations)
  → Custom IRMs deployed by third parties
  → Periphery contracts (not in this repo)
  → Cross-protocol integrations built ON Aave
  → Governance proposals that change parameters

LESSON:
  → Mature protocols (Aave, Morpho) = extremely hard to find bugs
  → Their EXTENSIONS and INTEGRATIONS = better targets
  → New deployments on new chains = less audited
  → Focus on the EDGES, not the core
```

---

*BOZAGENTIC · "Aave wrote the textbook. Morpho wrote the minimal version. Arcadia skipped the chapter on inflation attacks."*
