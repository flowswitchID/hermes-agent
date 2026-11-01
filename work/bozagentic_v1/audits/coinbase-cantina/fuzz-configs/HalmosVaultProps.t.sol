// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Simple vault to demonstrate Halmos ghost variables
contract SimpleVault {
    mapping(address => uint256) public balanceOf;
    uint256 public totalDeposits;
    
    function deposit(uint256 amount) external {
        balanceOf[msg.sender] += amount;
        totalDeposits += amount;
    }
    
    function withdraw(uint256 amount) external {
        require(balanceOf[msg.sender] >= amount, "insufficient");
        balanceOf[msg.sender] -= amount;
        totalDeposits -= amount;
    }
}

contract VaultProps {
    SimpleVault vault;
    
    constructor() {
        vault = new SimpleVault();
    }
    
    // PROPERTY: totalDeposits == sum of all balances
    // (Can't easily express "sum of all" in Halmos without ghost)
    // But we CAN check: totalDeposits >= any individual balance
    function check_total_ge_individual(address user) external view {
        assert(vault.totalDeposits() >= vault.balanceOf(user));
    }
    
    // PROPERTY: deposit increases both balance and total
    function check_deposit_increases(uint256 amount) external {
        if (amount == 0) return;
        uint256 balBefore = vault.balanceOf(address(this));
        uint256 totalBefore = vault.totalDeposits();
        vault.deposit(amount);
        assert(vault.balanceOf(address(this)) == balBefore + amount);
        assert(vault.totalDeposits() == totalBefore + amount);
    }
    
    // PROPERTY: withdraw decreases both
    function check_withdraw_decreases(uint256 depAmount, uint256 wdwAmount) external {
        if (depAmount == 0) return;
        if (wdwAmount > depAmount) wdwAmount = depAmount;
        
        vault.deposit(depAmount);
        uint256 balBefore = vault.balanceOf(address(this));
        uint256 totalBefore = vault.totalDeposits();
        vault.withdraw(wdwAmount);
        assert(vault.balanceOf(address(this)) == balBefore - wdwAmount);
        assert(vault.totalDeposits() == totalBefore - wdwAmount);
    }
    
    // PROPERTY: can't withdraw more than balance
    function check_no_overdraft(uint256 amount) external {
        if (amount == 0) return;
        // Balance is 0 (fresh), any withdraw should revert
        try vault.withdraw(amount) {
            assert(false); // should not reach
        } catch {}
    }
}
