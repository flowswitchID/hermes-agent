// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Test.sol";
import "../src/ERC4626Vault.sol";

/// @notice Halmos symbolic verification for ERC4626 invariants
/// @dev Run: halmos --contract ERC4626Props
contract ERC4626Props is Test {
    ERC4626Vault vault;
    MockERC20 token;

    address alice = address(0xA11CE);
    address bob = address(0xB0B);

    function setUp() public {
        token = new MockERC20();
        vault = new ERC4626Vault(address(token));

        // Fund users
        token.mint(alice, 1_000_000e18);
        token.mint(bob, 1_000_000e18);

        vm.prank(alice);
        token.approve(address(vault), type(uint256).max);
        vm.prank(bob);
        token.approve(address(vault), type(uint256).max);
    }

    // ═══════════════════════════════════════════════════════════
    // INVARIANT 1: Deposit-Redeem Roundtrip ≤ 1 wei loss
    // "If I deposit X assets and immediately redeem, I lose at most 1 wei"
    // ═══════════════════════════════════════════════════════════
    function check_depositRedeem_roundtrip(uint256 amount) public {
        vm.assume(amount > 0 && amount < 500_000e18);

        // Alice deposits
        vm.prank(alice);
        uint256 shares = vault.deposit(amount, alice);

        // Alice immediately redeems all shares
        vm.prank(alice);
        uint256 assetsOut = vault.redeem(shares, alice, alice);

        // INVARIANT: loss ≤ 1 wei (rounding)
        assertLe(amount - assetsOut, 1, "ROUNDTRIP_LOSS_EXCEEDS_1_WEI");
    }

    // ═══════════════════════════════════════════════════════════
    // INVARIANT 2: Redeem-Deposit Roundtrip ≤ 1 wei loss
    // ═══════════════════════════════════════════════════════════
    function check_redeemDeposit_roundtrip(uint256 amount) public {
        vm.assume(amount > 1 && amount < 500_000e18);

        // Setup: Alice has shares
        vm.prank(alice);
        vault.deposit(amount, alice);
        uint256 shares = vault.balanceOf(alice);
        vm.assume(shares > 0);

        // Redeem all
        vm.prank(alice);
        uint256 assetsOut = vault.redeem(shares, alice, alice);

        // Re-deposit the output
        vm.prank(alice);
        uint256 newShares = vault.deposit(assetsOut, alice);

        // INVARIANT: newShares ≤ original shares (rounding favors vault)
        assertLe(newShares, shares, "REDEEM_DEPOSIT_GAINS_SHARES");
    }

    // ═══════════════════════════════════════════════════════════
    // INVARIANT 3: Total shares = sum of all balances
    // "No phantom shares can exist"
    // ═══════════════════════════════════════════════════════════
    function check_totalSupply_consistency(uint256 amtA, uint256 amtB) public {
        vm.assume(amtA > 0 && amtA < 500_000e18);
        vm.assume(amtB > 0 && amtB < 500_000e18);

        vm.prank(alice);
        vault.deposit(amtA, alice);
        vm.prank(bob);
        vault.deposit(amtB, bob);

        // INVARIANT: totalSupply == balanceOf(alice) + balanceOf(bob)
        assertEq(
            vault.totalSupply(),
            vault.balanceOf(alice) + vault.balanceOf(bob),
            "PHANTOM_SHARES"
        );
    }

    // ═══════════════════════════════════════════════════════════
    // INVARIANT 4: Inflation attack resistance
    // "After first deposit of 1 wei, second deposit still gets shares"
    // ═══════════════════════════════════════════════════════════
    function check_inflation_attack_resistance(uint256 donation) public {
        vm.assume(donation > 0 && donation < 500_000e18);

        // Attacker deposits 1 wei
        vm.prank(alice);
        vault.deposit(1, alice);

        // Attacker donates directly
        vm.prank(alice);
        token.transfer(address(vault), donation);

        // Victim deposits
        vm.prank(bob);
        uint256 shares = vault.deposit(1e18, bob);

        // INVARIANT: victim MUST get shares > 0
        assertGt(shares, 0, "INFLATION_ATTACK_VICTIM_GETS_ZERO_SHARES");
    }

    // ═══════════════════════════════════════════════════════════
    // INVARIANT 5: Withdraw never gives more than deposited
    // "Vault is solvent: total withdrawals ≤ total deposits"
    // ═══════════════════════════════════════════════════════════
    function check_solvency(uint256 amtA, uint256 amtB) public {
        vm.assume(amtA > 0 && amtA < 500_000e18);
        vm.assume(amtB > 0 && amtB < 500_000e18);

        vm.prank(alice);
        vault.deposit(amtA, alice);
        vm.prank(bob);
        vault.deposit(amtB, bob);

        uint256 totalDeposited = amtA + amtB;

        // Both withdraw max
        uint256 maxA = vault.maxWithdraw(alice);
        uint256 maxB = vault.maxWithdraw(bob);

        // INVARIANT: total withdrawable ≤ total deposited
        assertLe(maxA + maxB, totalDeposited, "INSOLVENT_VAULT");
    }

    // ═══════════════════════════════════════════════════════════
    // INVARIANT 6: convertToShares and convertToAssets are inverse (±1)
    // ═══════════════════════════════════════════════════════════
    function check_conversion_inverse(uint256 assets) public {
        vm.assume(assets > 0 && assets < 500_000e18);

        // Setup some state
        vm.prank(alice);
        vault.deposit(100e18, alice);

        uint256 shares = vault.convertToShares(assets);
        uint256 backToAssets = vault.convertToAssets(shares);

        // INVARIANT: roundtrip conversion loss ≤ 1
        if (assets >= backToAssets) {
            assertLe(assets - backToAssets, 1, "CONVERSION_LOSS_EXCEEDS_1");
        } else {
            assertLe(backToAssets - assets, 1, "CONVERSION_GAIN_EXCEEDS_1");
        }
    }

    // ═══════════════════════════════════════════════════════════
    // INVARIANT 7: Monotonicity — more assets = more shares
    // ═══════════════════════════════════════════════════════════
    function check_monotonicity(uint256 a, uint256 b) public {
        vm.assume(a < b && b < 500_000e18);

        // Setup state
        vm.prank(alice);
        vault.deposit(100e18, alice);

        uint256 sharesA = vault.convertToShares(a);
        uint256 sharesB = vault.convertToShares(b);

        // INVARIANT: a < b → shares(a) ≤ shares(b)
        assertLe(sharesA, sharesB, "MONOTONICITY_VIOLATED");
    }

    // ═══════════════════════════════════════════════════════════
    // INVARIANT 8: Deposit mints exactly previewDeposit shares
    // ═══════════════════════════════════════════════════════════
    function check_preview_matches_deposit(uint256 amount) public {
        vm.assume(amount > 0 && amount < 500_000e18);

        // Setup state
        vm.prank(alice);
        vault.deposit(100e18, alice);

        uint256 expected = vault.previewDeposit(amount);

        vm.prank(bob);
        uint256 actual = vault.deposit(amount, bob);

        // INVARIANT: preview == actual
        assertEq(actual, expected, "PREVIEW_MISMATCH");
    }
}
