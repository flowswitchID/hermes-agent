# MORPHO BLUE — CODE REFERENCE & PATTERNS
# Belajar dari protocol paling clean di DeFi
# BOZAGENTIC · 2026-07-30

---

## 1. ARCHITECTURE PATTERN: "One Contract, No Inheritance"

```solidity
// Morpho: 555 lines, 1 contract, 0 inheritance
contract Morpho is IMorphoStaticTyping {
    // Semua logic di 1 file
    // Libraries untuk math/utils (bukan inheritance)
    // Interface untuk external calls
}

// KENAPA INI BAGUS:
// → No diamond problem
// → No storage collision dari inheritance
// → No "which parent does this come from?"
// → Auditor bisa baca 1 file dan paham SEMUA
// → Compiler bisa optimize lebih baik

// KAPAN PAKAI:
// → Protocol core (lending, DEX, vault)
// → Kalau total logic < 1000 lines
// → Kalau nggak butuh polymorphism

// KAPAN JANGAN:
// → Plugin system (butuh inheritance)
// → Upgradeable (butuh base contract)
// → > 2000 lines (pecah jadi modules)
```

---

## 2. SHARE MATH PATTERN: Virtual Shares Done Right

```solidity
// Morpho SharesMathLib — THE reference implementation
library SharesMathLib {
    uint256 internal constant VIRTUAL_SHARES = 1e6;
    uint256 internal constant VIRTUAL_ASSETS = 1;

    function toSharesDown(uint256 assets, uint256 totalAssets, uint256 totalShares)
        internal pure returns (uint256) {
        return assets.mulDivDown(totalShares + VIRTUAL_SHARES, totalAssets + VIRTUAL_ASSETS);
    }

    function toAssetsDown(uint256 shares, uint256 totalAssets, uint256 totalShares)
        internal pure returns (uint256) {
        return shares.mulDivDown(totalAssets + VIRTUAL_ASSETS, totalShares + VIRTUAL_SHARES);
    }

    function toSharesUp(uint256 assets, uint256 totalAssets, uint256 totalShares)
        internal pure returns (uint256) {
        return assets.mulDivUp(totalShares + VIRTUAL_SHARES, totalAssets + VIRTUAL_ASSETS);
    }

    function toAssetsUp(uint256 shares, uint256 totalAssets, uint256 totalShares)
        internal pure returns (uint256) {
        return shares.mulDivUp(totalAssets + VIRTUAL_ASSETS, totalShares + VIRTUAL_SHARES);
    }
}

// KENAPA INI BAGUS:
// → VIRTUAL_SHARES = 1e6 (bukan 0 kayak Arcadia, bukan 1 kayak OZ default)
// → 4 functions: Down/Up × Shares/Assets
// → Rounding CONSISTENT: deposit pakai Down (user dapet lebih sedikit)
//                        withdraw pakai Up (user bayar lebih banyak)
// → Selalu favor protocol

// RULE:
// supply:  assets → shares = toSharesDown (user dapet minimal)
// withdraw: assets → shares = toSharesUp  (user bayar maksimal)
// borrow:  assets → shares = toSharesUp   (borrower bayar maksimal)
// repay:   assets → shares = toSharesDown (borrower dapet minimal)
// liquidate: repaid → shares = toSharesUp (liquidator bayar maksimal)

// PERBANDINGAN:
// Arcadia: VAS = 0 → inflation attack possible
// OZ:      _decimalsOffset() = 0 → virtual shares = 1 (minimal)
// Morpho:  VIRTUAL_SHARES = 1e6 → attack cost = $1M+ (prohibitive)
```

---

## 3. STORED ACCOUNTING PATTERN: Never Use balanceOf()

```solidity
// Morpho: STORED accounting
market[id].totalSupplyAssets += assets;   // explicit tracking
market[id].totalBorrowAssets += interest;  // explicit tracking

// BUKAN:
// totalAssets = token.balanceOf(address(this));  ← DANGEROUS

// KENAPA INI BAGUS:
// → Direct token transfer nggak ngaruh ke accounting
// → Nggak ada "donate" attack vector
// → Nggak ada "skim" attack vector
// → Accounting selalu consistent (kecuali bug di logic)

// KENAPA balanceOf() DANGEROUS:
// → Basin: sync() baca balanceOf() → donation attack
// → Arcadia: totalAssets() = balanceOf() → inflate via donate
// → Siapa aja bisa kirim token → manipulate accounting

// RULE:
// → Track semua token flow secara explicit
// → totalSupplyAssets += deposit, -= withdraw
// → totalBorrowAssets += borrow + interest, -= repay
// → JANGAN pernah derive dari balanceOf()

// EXCEPTION (kapan balanceOf() OK):
// → flashLoan: transfer → callback → transferFrom (balance check implicit)
// → View functions untuk reporting (bukan accounting)
```

---

## 4. OPTIMISTIC ACCOUNTING PATTERN: No ReentrancyGuard Needed

```solidity
// Morpho supply():
function supply(...) external returns (uint256, uint256) {
    _accrueInterest(marketParams, id);
    
    // 1. UPDATE STATE FIRST
    position[id][onBehalf].supplyShares += shares;
    market[id].totalSupplyShares += shares;
    market[id].totalSupplyAssets += assets;
    
    // 2. CALLBACK (optional)
    if (data.length > 0) IMorphoSupplyCallback(msg.sender).onMorphoSupply(assets, data);
    
    // 3. TRANSFER LAST
    IERC20(marketParams.loanToken).safeTransferFrom(msg.sender, address(this), assets);
}

// KENAPA INI SAFE TANPA ReentrancyGuard:
// → State udah di-update SEBELUM callback
// → Re-enter supply() = harus bayar tokens lagi (no free shares)
// → Re-enter withdraw() = shares udah berkurang (no double withdraw)
// → Setiap re-entry butuh PAYMENT → no profit dari reentrancy

// KENAPA INI LEBIH BAIK DARI ReentrancyGuard:
// → Hemat ~20K gas per call (no SSTORE for lock)
// → Nggak perlu worry soal cross-function reentrancy
// → Simpler code (no modifier)
// → Enables flash-loan-like patterns (callback before payment)

// KAPAN PAKAI:
// → Setiap state change diikuti oleh transfer
// → Transfer adalah "payment" untuk state change
// → Re-entry = bayar lagi = no profit

// KAPAN JANGAN (tetap pakai ReentrancyGuard):
// → State change yang nggak butuh payment
// → External call yang nggak transfer tokens
// → Complex multi-step operations
```

---

## 5. INPUT VALIDATION PATTERN: exactlyOneZero

```solidity
// Morpho: user passes EITHER assets OR shares, never both
require(UtilsLib.exactlyOneZero(assets, shares), ErrorsLib.INCONSISTENT_INPUT);

// Implementation (assembly for gas):
function exactlyOneZero(uint256 x, uint256 y) internal pure returns (bool z) {
    assembly {
        z := xor(iszero(x), iszero(y))
    }
}

// KENAPA INI BAGUS:
// → User bisa specify "I want to deposit 100 USDC" (assets mode)
// → Atau "I want exactly 50 shares" (shares mode)
// → Nggak bisa dua-duanya (ambiguous)
// → Nggak bisa dua-duanya 0 (no-op)

// PATTERN:
// if (assets > 0) shares = assets.toSharesDown(...);  // compute shares
// else assets = shares.toAssetsUp(...);              // compute assets

// KAPAN PAKAI:
// → Setiap function yang accept "amount in X or Y"
// → deposit(assets, shares) — specify one
// → withdraw(assets, shares) — specify one
// → liquidate(seizedAssets, repaidShares) — specify one
```

---

## 6. UINT128 CAP PATTERN: Overflow Prevention

```solidity
// Morpho: all stored values capped at uint128
market[id].totalSupplyAssets += assets.toUint128();
market[id].totalBorrowShares += shares.toUint128();

// toUint128:
function toUint128(uint256 x) internal pure returns (uint128) {
    require(x <= type(uint128).max, ErrorsLib.MAX_UINT128_EXCEEDED);
    return uint128(x);
}

// KENAPA INI BAGUS:
// → Storage packing: 2 uint128 in 1 slot (hemat gas)
// → Explicit overflow check (bukan silent wrap)
// → uint128 max = 3.4e38 → cukup untuk semua realistic values
// → Kalau exceed = revert (bukan silent corruption)

// STORAGE LAYOUT:
struct Market {
    uint128 totalSupplyAssets;  // slot N
    uint128 totalSupplyShares;  // slot N (packed)
    uint128 totalBorrowAssets;  // slot N+1
    uint128 totalBorrowShares;  // slot N+1 (packed)
    uint128 lastUpdate;         // slot N+2
    uint128 fee;                // slot N+2 (packed)
}
// 3 slots untuk seluruh market state!
```

---

## 7. SAFE TRANSFER PATTERN: Handle All Token Quirks

```solidity
// Morpho SafeTransferLib:
function safeTransfer(IERC20 token, address to, uint256 value) internal {
    require(address(token).code.length > 0, ErrorsLib.NO_CODE);
    
    (bool success, bytes memory returndata) =
        address(token).call(abi.encodeCall(IERC20Internal.transfer, (to, value)));
    
    require(success, ErrorsLib.TRANSFER_REVERTED);
    require(returndata.length == 0 || abi.decode(returndata, (bool)), 
            ErrorsLib.TRANSFER_RETURNED_FALSE);
}

// KENAPA INI BAGUS:
// 1. code.length > 0 → prevent transfer to EOA (no code = no token)
// 2. Low-level call → works with non-standard tokens
// 3. success check → handles reverts
// 4. returndata check → handles USDT (no return value)
// 5. abi.decode(bool) → handles standard ERC20 (returns true/false)

// HANDLES:
// ✅ Standard ERC20 (returns bool)
// ✅ USDT (returns nothing)
// ✅ Rebasing tokens (AMPL, stETH)
// ✅ Fee-on-transfer tokens (PAXG)
// ❌ Tokens that return random bytes (will revert — by design)

// COMPARISON:
// OZ SafeERC20: similar but more code
// Solmate SafeTransferLib: assembly-optimized (less readable)
// Morpho: middle ground (readable + handles all cases)
```

---

## 8. INTEREST RATE PATTERN: Taylor Approximation

```solidity
// Morpho: continuous compounding approximation
function wTaylorCompounded(uint256 x, uint256 n) internal pure returns (uint256) {
    uint256 firstTerm = x * n;
    uint256 secondTerm = mulDivDown(firstTerm, firstTerm, 2 * WAD);
    uint256 thirdTerm = mulDivDown(secondTerm, firstTerm, 3 * WAD);
    return firstTerm + secondTerm + thirdTerm;
}

// Math: e^(nx) - 1 ≈ nx + (nx)²/2 + (nx)³/6
// x = borrow rate per second (WAD)
// n = elapsed seconds

// KENAPA INI BAGUS:
// → Gas efficient (3 multiplications vs exp() which is expensive)
// → Accurate for realistic rates (x*n < 1e17)
// → No external library needed
// → Deterministic (no precision issues)

// ACCURACY:
// 10% APY, 1 year: error < 0.001%
// 100% APY, 1 year: error < 1%
// 1000% APY, 1 year: error ~10% (unrealistic rate)

// KAPAN PAKAI:
// → Interest rate calculations
// → Any continuous compounding approximation
// → When gas matters and rates are bounded

// KAPAN JANGAN:
// → When x*n > 1e18 (approximation diverges)
// → When exact precision is required
// → Use PRB-Math exp() for exact results
```

---

## 9. AUTHORIZATION PATTERN: EIP-712 + Nonce

```solidity
// Morpho: gasless authorization via signature
function setAuthorizationWithSig(Authorization memory authorization, Signature calldata signature) external {
    require(block.timestamp <= authorization.deadline, ErrorsLib.SIGNATURE_EXPIRED);
    require(authorization.nonce == nonce[authorization.authorizer]++, ErrorsLib.INVALID_NONCE);
    
    bytes32 hashStruct = keccak256(abi.encode(AUTHORIZATION_TYPEHASH, authorization));
    bytes32 digest = keccak256(bytes.concat("\x19\x01", DOMAIN_SEPARATOR, hashStruct));
    address signatory = ecrecover(digest, signature.v, signature.r, signature.s);
    
    require(signatory != address(0) && authorization.authorizer == signatory, ErrorsLib.INVALID_SIGNATURE);
    
    isAuthorized[authorization.authorizer][authorization.authorized] = authorization.isAuthorized;
}

// KENAPA INI BAGUS:
// → Nonce prevents replay (incremented each time)
// → Deadline prevents stale signatures
// → DOMAIN_SEPARATOR includes chainId (cross-chain replay safe)
// → ecrecover returns address(0) for invalid sig (checked)
// → Nonce increment is SIDE EFFECT (desired even if auth already set)

// PATTERN:
// DOMAIN_SEPARATOR = keccak256("EIP712Domain(uint256 chainId,address verifyingContract)")
// → Computed in constructor (immutable)
// → Includes chainId → safe across forks
// → Includes address → safe across deployments
```

---

## 10. LIQUIDATION PATTERN: Incentive Factor

```solidity
// Morpho: liquidation incentive
uint256 liquidationIncentiveFactor = UtilsLib.min(
    MAX_LIQUIDATION_INCENTIVE_FACTOR,  // cap at 1.15 (15%)
    WAD.wDivDown(WAD - LIQUIDATION_CURSOR.wMulDown(WAD - marketParams.lltv))
);

// Formula: min(1.15, 1 / (1 - 0.3 * (1 - lltv)))
// lltv = 0.8 → incentive = min(1.15, 1/(1-0.06)) = min(1.15, 1.064) = 1.064
// lltv = 0.5 → incentive = min(1.15, 1/(1-0.15)) = min(1.15, 1.176) = 1.15
// lltv = 0.3 → incentive = min(1.15, 1/(1-0.21)) = min(1.15, 1.266) = 1.15

// KENAPA INI BAGUS:
// → Higher LLTV → lower incentive (less risky position)
// → Lower LLTV → higher incentive (more risky, needs more incentive)
// → Capped at 15% (prevents excessive penalty)
// → Deterministic (no oracle for incentive)

// BAD DEBT HANDLING:
// If collateral == 0 after seizure:
//   badDebtAssets subtracted from BOTH totalBorrowAssets AND totalSupplyAssets
//   → Suppliers absorb loss proportionally
//   → No cascade to other markets
//   → No pool bricking
```

---

## 11. CALLBACK PATTERN: Flash-Loan-Like

```solidity
// Morpho: 5 callback interfaces
interface IMorphoSupplyCallback {
    function onMorphoSupply(uint256 assets, bytes calldata data) external;
}
interface IMorphoRepayCallback {
    function onMorphoRepay(uint256 assets, bytes calldata data) external;
}
interface IMorphoLiquidateCallback {
    function onMorphoLiquidate(uint256 repaidAssets, bytes calldata data) external;
}
interface IMorphoSupplyCollateralCallback {
    function onMorphoSupplyCollateral(uint256 assets, bytes calldata data) external;
}
interface IMorphoFlashLoanCallback {
    function onMorphoFlashLoan(uint256 assets, bytes calldata data) external;
}

// USAGE:
// if (data.length > 0) IMorphoSupplyCallback(msg.sender).onMorphoSupply(assets, data);

// KENAPA INI BAGUS:
// → Enables atomic operations (swap + supply in 1 tx)
// → Enables flash loans (borrow → use → repay in 1 tx)
// → Optional (data.length == 0 → skip callback)
// → Caller implements interface (not Morpho's responsibility)

// SECURITY MODEL:
// → Callback to msg.sender (not arbitrary address)
// → State already updated before callback
// → Transfer happens AFTER callback
// → Re-entry requires payment → no free profit
```

---

## 12. MARKET ISOLATION PATTERN

```solidity
// Morpho: each market is completely independent
mapping(Id => Market) public market;
mapping(Id => mapping(address => Position)) public position;
mapping(Id => MarketParams) public idToMarketParams;

// Market ID = keccak256(loanToken, collateralToken, oracle, irm, lltv)
// → Each combination = separate market
// → Separate accounting
// → Separate bad debt
// → Separate liquidation

// KENAPA INI BAGUS:
// → Bad debt in WETH/USDC market doesn't affect WBTC/USDC market
// → No cascade risk
// → No "pool bricking"
// → Market creators choose their own oracle + IRM
// → Users choose which markets to trust

// COMPARISON:
// Aave: shared pool (cascade risk)
// Compound: per-market (similar to Morpho)
// Arcadia: tranche system (cascade through tranches)
// Morpho: per-market + no tranches (maximum isolation)
```

---

## 13. GAS OPTIMIZATION PATTERNS

```solidity
// 1. Assembly for simple operations
function min(uint256 x, uint256 y) internal pure returns (uint256 z) {
    assembly { z := xor(x, mul(xor(x, y), lt(y, x))) }
}
// Saves: ~10 gas vs Solidity if/else

// 2. zeroFloorSub (no underflow check needed)
function zeroFloorSub(uint256 x, uint256 y) internal pure returns (uint256 z) {
    assembly { z := mul(gt(x, y), sub(x, y)) }
}
// Returns max(0, x-y) without require

// 3. Storage packing (uint128)
// 2 values per slot instead of 1
// Saves: 20K gas per additional slot avoided

// 4. No ReentrancyGuard
// Saves: ~20K gas per call (no SSTORE for lock)

// 5. Callback before transferFrom
// Enables atomic operations without flash loan premium
// Saves: flash loan fee (Morpho charges 0)

// 6. extSloads (batch storage read)
function extSloads(bytes32[] calldata slots) external view returns (bytes32[] memory) {
    // Single call to read N storage slots
    // Saves: N-1 external calls for off-chain indexers
}
```

---

## 14. ERROR HANDLING PATTERN

```solidity
// Morpho: string errors (not custom errors)
require(msg.sender == owner, ErrorsLib.NOT_OWNER);
// ErrorsLib.NOT_OWNER = "not owner"

// KENAPA STRING (bukan custom errors):
// → Solidity 0.8.19 (custom errors available since 0.8.4)
// → String errors: more readable in explorers
// → Custom errors: ~50 gas cheaper per revert
// → Morpho chose readability over gas (reverts are rare)

// PATTERN:
// → All errors in ErrorsLib (single source of truth)
// → Descriptive names: NOT_OWNER, MARKET_NOT_CREATED, INSUFFICIENT_COLLATERAL
// → No error codes (human-readable)

// ALTERNATIVE (custom errors — more gas efficient):
error NotOwner();
error MarketNotCreated();
error InsufficientCollateral();
// Saves ~50 gas per revert, but less readable
```

---

## 15. CHECKLIST: "Morpho-Quality" Code

```
Sebelum submit code, cek:

□ Single contract (< 1000 lines)?
□ No inheritance (use libraries)?
□ Stored accounting (no balanceOf)?
□ Virtual shares for ERC4626?
□ Rounding consistent (favor protocol)?
□ exactlyOneZero for dual-input?
□ uint128 caps with explicit check?
□ SafeTransferLib handles all token quirks?
□ Callback pattern (state → callback → transfer)?
□ Per-market/per-pool isolation?
□ EIP-712 with nonce + deadline + chainId?
□ No ReentrancyGuard (optimistic accounting)?
□ All errors in single library?
□ Gas optimizations where they matter?
□ Comment explains WHY, not WHAT?
```

---

*BOZAGENTIC · "Morpho Blue: the textbook they should teach in Solidity school."*
