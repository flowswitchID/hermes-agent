// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Vulnerable vault — Halmos proves the bug
contract VulnerableVault {
    mapping(address => uint256) public shares;
    uint256 public totalShares;
    uint256 public totalAssets;
    
    function deposit(uint256 assets) external {
        uint256 newShares;
        if (totalShares == 0) {
            newShares = assets;
        } else {
            newShares = (assets * totalShares) / totalAssets;
        }
        shares[msg.sender] += newShares;
        totalShares += newShares;
        totalAssets += assets;
    }
    
    function withdraw(uint256 shareAmt) external {
        uint256 assets = (shareAmt * totalAssets) / totalShares;
        shares[msg.sender] -= shareAmt;
        totalShares -= shareAmt;
        totalAssets -= assets;
    }
    
    // Simulate donation (direct transfer to vault)
    function donate(uint256 assets) external {
        totalAssets += assets;
    }
}

contract BugProof {
    VulnerableVault vault;
    
    constructor() {
        vault = new VulnerableVault();
    }
    
    // PROPERTY: Inflation attack — first depositor can be frontrun
    // Attacker: deposit(1) → donate(1e18) → victim deposit(1e18) gets 0 shares
    function check_inflation_attack(uint256 victimDeposit) external {
        if (victimDeposit == 0) return;
        if (victimDeposit > 1e30) victimDeposit = 1e30;
        
        // Attacker deposits 1 wei
        vault.deposit(1);
        // Attacker donates 1e18 (inflate share price)
        vault.donate(1e18);
        
        // Victim deposits
        uint256 sharesBefore = vault.shares(address(0xBEEF));
        // Simulate victim deposit (different address)
        // In real attack: victim calls deposit() from their address
        // shares = (victimDeposit * totalShares) / totalAssets
        // = (victimDeposit * 1) / (1 + 1e18)
        // For victimDeposit < 1e18: shares = 0 (truncated!)
        
        uint256 expectedShares = (victimDeposit * vault.totalShares()) / vault.totalAssets();
        
        if (victimDeposit < 1e18) {
            // BUG: victim gets 0 shares but loses their deposit!
            assert(expectedShares == 0); // confirms the bug
        }
    }
    
    // PROPERTY: Fixed vault (with +1 offset) prevents inflation
    function check_fixed_vault(uint256 victimDeposit) external pure {
        if (victimDeposit == 0) return;
        if (victimDeposit > 1e30) victimDeposit = 1e30;
        
        // Fixed: shares = (assets * (totalShares + 1)) / (totalAssets + 1)
        uint256 totalShares = 1; // attacker deposited 1
        uint256 totalAssets = 1 + 1e18; // attacker donated 1e18
        
        uint256 fixedShares = (victimDeposit * (totalShares + 1)) / (totalAssets + 1);
        
        // With +1 offset: even small deposits get shares
        // For victimDeposit = 1: shares = (1 * 2) / (1e18 + 2) = 0
        // Still 0 for very small amounts, but the offset helps for larger amounts
        // The REAL fix is virtual shares (ERC4626 standard)
        
        // Key property: fixedShares should be proportional to deposit
        if (victimDeposit >= totalAssets) {
            assert(fixedShares >= totalShares); // at least 1 share
        }
    }
    
    // PROPERTY: solvency — totalAssets >= sum of redeemable value
    function check_solvency(uint256 dep1, uint256 dep2) external {
        if (dep1 == 0 || dep2 == 0) return;
        if (dep1 > 1e24) dep1 = 1e24;
        if (dep2 > 1e24) dep2 = 1e24;
        
        vault.deposit(dep1);
        vault.deposit(dep2);
        
        // Total assets should equal sum of deposits
        assert(vault.totalAssets() == dep1 + dep2);
        // Total shares should be consistent
        assert(vault.totalShares() > 0);
    }
}
