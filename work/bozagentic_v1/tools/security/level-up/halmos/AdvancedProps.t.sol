// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "../src/LendingProtocol.sol";

/// @title Advanced Halmos properties with svm cheatcodes
contract AdvancedProps {
    MiniVault vault;
    
    constructor() {
        vault = new MiniVault();
    }
    
    // ERC4626 inflation attack proof
    // Property: For any deposit amount, attacker cannot profit from donation
    function check_inflationAttackUnprofitable(
        uint256 attackerDeposit,
        uint256 donation,
        uint256 victimDeposit
    ) public {
        require(attackerDeposit >= 1 && attackerDeposit <= 1e24, "range");
        require(donation >= 1 && donation <= 1e30, "range");
        require(victimDeposit >= 1e18 && victimDeposit <= 1e24, "range");
        
        // Attacker deposits first
        uint256 attackerShares = vault.deposit(attackerDeposit);
        
        // Attacker donates
        vault.simulateDonation(donation);
        
        // Victim deposits
        uint256 victimShares = vault.deposit(victimDeposit);
        
        // Attacker withdraws
        uint256 attackerWithdraw = vault.withdraw(attackerShares);
        
        // Property: attacker must NOT profit
        // profit = attackerWithdraw - attackerDeposit
        assert(attackerWithdraw <= attackerDeposit + 1); // +1 for rounding
    }
    
    // Share monotonicity: more deposit = more shares
    function check_shareMonotonicity(uint256 amt1, uint256 amt2) public {
        require(amt1 >= 1e18 && amt1 <= 1e24, "range");
        require(amt2 >= 1e18 && amt2 <= 1e24, "range");
        require(amt2 > amt1, "ordering");
        
        // Fresh vault for each check
        MiniVault v = new MiniVault();
        
        uint256 shares1 = v.deposit(amt1);
        
        MiniVault v2 = new MiniVault();
        uint256 shares2 = v2.deposit(amt2);
        
        // More deposit → more shares (first depositor: 1:1)
        assert(shares2 > shares1);
    }
    
    // Withdrawal ordering: partial withdraw leaves correct balance
    function check_partialWithdraw(uint256 depositAmt, uint256 withdrawPct) public {
        require(depositAmt >= 1e18 && depositAmt <= 1e24, "range");
        require(withdrawPct >= 1 && withdrawPct <= 100, "range");
        
        uint256 sharesMinted = vault.deposit(depositAmt);
        uint256 sharesToWithdraw = (sharesMinted * withdrawPct) / 100;
        
        if (sharesToWithdraw == 0) return;
        
        uint256 assetsOut = vault.withdraw(sharesToWithdraw);
        uint256 remainingShares = vault.shares(address(this));
        
        // Remaining shares should be proportional
        assert(remainingShares == sharesMinted - sharesToWithdraw);
        
        // Assets out should be proportional
        uint256 expectedOut = (sharesToWithdraw * depositAmt) / sharesMinted;
        assert(assetsOut <= expectedOut + 1); // rounding tolerance
    }
    
    // Cross-function: deposit then donate then withdraw
    function check_donationWithdrawInteraction(uint256 dep, uint256 don) public {
        require(dep >= 1e18 && dep <= 1e24, "range");
        require(don >= 1 && don <= 1e24, "range");
        
        uint256 shares = vault.deposit(dep);
        vault.simulateDonation(don);
        
        uint256 withdrawable = vault.previewWithdraw(shares);
        
        // After donation, withdrawable > deposited (donation benefits depositor)
        assert(withdrawable >= dep);
        
        // But not more than total assets
        assert(withdrawable <= vault.totalAssets());
    }
}
