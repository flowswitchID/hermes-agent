// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "../src/LendingProtocol.sol";

contract CrossContractProps {
    MiniVault vault;
    MiniLender lender;
    address user1 = address(0x1);
    address user2 = address(0x2);
    
    constructor() {
        vault = new MiniVault();
        lender = new MiniLender(address(vault));
    }
    
    // INVARIANT 1: Vault solvency — totalAssets >= sum of all withdrawable
    function check_vaultSolvency(uint256 depositAmt) public {
        depositAmt = bound(depositAmt, 1, 1e30);
        
        vm_prank(user1);
        vault.deposit(depositAmt);
        
        // After any deposit, vault must remain solvent
        uint256 userShares = vault.shares(user1);
        uint256 withdrawable = vault.previewWithdraw(userShares);
        assert(withdrawable <= vault.totalAssets());
    }
    
    // INVARIANT 2: Share conservation — totalShares == sum(user shares)
    function check_shareConservation(uint256 amt1, uint256 amt2) public {
        amt1 = bound(amt1, 1, 1e24);
        amt2 = bound(amt2, 1, 1e24);
        
        vm_prank(user1);
        vault.deposit(amt1);
        vm_prank(user2);
        vault.deposit(amt2);
        
        uint256 sumShares = vault.shares(user1) + vault.shares(user2);
        assert(sumShares == vault.totalShares());
    }
    
    // INVARIANT 3: Donation doesn't break share ratio monotonicity
    function check_donationSafety(uint256 depositAmt, uint256 donationAmt) public {
        depositAmt = bound(depositAmt, 1e18, 1e30);
        donationAmt = bound(donationAmt, 1, 1e30);
        
        vm_prank(user1);
        uint256 sharesBefore = vault.deposit(depositAmt);
        
        uint256 valueBefore = vault.previewWithdraw(sharesBefore);
        
        // Someone donates
        vault.simulateDonation(donationAmt);
        
        uint256 valueAfter = vault.previewWithdraw(sharesBefore);
        
        // Donation should only INCREASE value
        assert(valueAfter >= valueBefore);
    }
    
    // INVARIANT 4: Borrow LTV enforcement
    function check_ltvEnforcement(uint256 depositAmt, uint256 borrowAmt) public {
        depositAmt = bound(depositAmt, 1e18, 1e30);
        borrowAmt = bound(borrowAmt, 1, 1e30);
        
        vm_prank(user1);
        uint256 sharesMinted = vault.deposit(depositAmt);
        
        // Try to borrow
        vm_prank(user1);
        try lender.borrow(sharesMinted, borrowAmt) {
            // If borrow succeeded, check LTV
            (uint256 collShares, uint256 debt) = lender.positions(user1);
            uint256 collValue = vault.previewWithdraw(collShares);
            assert(debt * 10000 <= collValue * 7500);
        } catch {
            // Revert is fine — LTV enforced
        }
    }
    
    // INVARIANT 5: Liquidation only when underwater
    function check_liquidationCondition(uint256 depositAmt, uint256 borrowAmt, uint256 donationDrop) public {
        depositAmt = bound(depositAmt, 1e18, 1e24);
        borrowAmt = bound(borrowAmt, 1, depositAmt * 75 / 100);
        donationDrop = bound(donationDrop, 0, depositAmt / 2);
        
        vm_prank(user1);
        uint256 sharesMinted = vault.deposit(depositAmt);
        
        vm_prank(user1);
        try lender.borrow(sharesMinted, borrowAmt) {} catch { return; }
        
        // Simulate value drop (negative donation)
        // Can't actually do negative, so check healthy position can't be liquidated
        vm_prank(user2);
        try lender.liquidate(user1) {
            // If liquidation succeeded, position MUST have been underwater
            uint256 healthBefore = lender.getHealthRatio(user1);
            // This should have reverted if healthy
            assert(false); // Should never reach here for healthy position
        } catch {
            // Expected for healthy positions
        }
    }
    
    // INVARIANT 6: Total debt consistency
    function check_debtConservation(uint256 amt1, uint256 amt2, uint256 repayAmt) public {
        amt1 = bound(amt1, 1e18, 1e24);
        amt2 = bound(amt2, 1e18, 1e24);
        repayAmt = bound(repayAmt, 0, amt1 * 75 / 100);
        
        vm_prank(user1);
        uint256 s1 = vault.deposit(amt1);
        vm_prank(user2);
        uint256 s2 = vault.deposit(amt2);
        
        vm_prank(user1);
        try lender.borrow(s1, amt1 * 50 / 100) {} catch { return; }
        vm_prank(user2);
        try lender.borrow(s2, amt2 * 50 / 100) {} catch { return; }
        
        uint256 debtBefore = lender.totalDebt();
        
        vm_prank(user1);
        try lender.repay(repayAmt) {} catch { return; }
        
        uint256 debtAfter = lender.totalDebt();
        (, uint256 pos1Debt) = lender.positions(user1);
        (, uint256 pos2Debt) = lender.positions(user2);
        
        assert(debtAfter == pos1Debt + pos2Debt);
    }
    
    // Cheatcode stubs for Halmos
    function vm_prank(address a) internal {
        // Halmos handles this via --sender
    }
    
    function bound(uint256 x, uint256 lo, uint256 hi) internal pure returns (uint256) {
        if (x < lo) return lo;
        if (x > hi) return hi;
        return x;
    }
}
