// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import "forge-std/Test.sol";

/// @title Aave V4 PoC - Flash Loan + Oracle Manipulation
/// @target 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2
contract AaveV4PoC is Test {
    address constant AAVE_POOL = 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2;
    address constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant USDC = 0xA0b86991c627Ce246199B89fF4b35b54C5c85687;
    address attacker = address(0xDEAD);

    function setUp() public {
        vm.createSelectFork("mainnet");
        vm.deal(attacker, 1 ether);
    }

    function test_flashLoanProfitability() public {
        vm.startPrank(attacker);
        // 1. Flash loan 1000 WETH
        // 2. Dump on Uniswap
        // 3. Borrow USDC at manipulated price
        // 4. Swap back, repay, check profit
        vm.stopPrank();
    }

    function test_liquidationBonus() public {
        // Verify bonus is 5-10%
    }

    function test_interestRateModel() public {
        // Verify borrowRate >= supplyRate
    }

    function test_healthFactor() public {
        // Verify HF = (collateral * liqThreshold) / debt
    }

    function test_eModeLTV() public {
        // Verify eMode LTV bounds
    }

    function invariant_solvency() public view {
        // totalAssets >= totalDebt
    }

    function invariant_noNegativeReserves() public view {
        // All reserve liquidity >= 0
    }
}
