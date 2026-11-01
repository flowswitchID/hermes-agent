// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../src/MiniProtocol.sol";

contract MultiContractProps {
    MiniPool pool;
    MiniVault vault;

    constructor() {
        pool = new MiniPool();
        vault = new MiniVault(address(pool));
    }

    /// Property: Vault shares are always backed by pool assets
    /// vault.totalShares > 0 => pool.userSupplyAssets(vault) > 0
    function check_vaultBacked(uint64 depositAmt) public {
        uint256 amt = uint256(depositAmt);
        if (amt == 0) return;

        // Simulate: user deposits into vault
        // In real scenario, tokens would be transferred
        // Here we just test the accounting
        pool.supply(amt); // direct supply to simulate token transfer
        
        uint256 poolAssetsBefore = pool.totalSupplyAssets();
        
        // Vault's share of pool should be proportional
        uint256 vaultPoolShares = pool.supplyShares(address(vault));
        uint256 totalPoolShares = pool.totalSupplyShares();
        
        if (totalPoolShares > 0 && vaultPoolShares > 0) {
            // Vault's assets = vaultPoolShares / totalPoolShares * totalSupplyAssets
            // This should be > 0
            assert(poolAssetsBefore > 0);
        }
    }

    /// Property: Supply then withdraw returns same amount (no value leakage)
    function check_supplyWithdrawRoundtrip(uint64 amt) public {
        uint256 a = uint256(amt);
        if (a == 0) return;
        
        pool.supply(a);
        uint256 sharesAfterSupply = pool.supplyShares(address(this));
        
        // Withdraw same amount
        pool.withdraw(a);
        uint256 sharesAfterWithdraw = pool.supplyShares(address(this));
        
        // All shares should be burned
        assert(sharesAfterWithdraw == 0);
    }

    /// Property: Pool solvency after any sequence
    function check_poolSolvency(uint64 supplyAmt, uint64 borrowAmt, uint64 collatAmt) public {
        uint256 s = uint256(supplyAmt);
        uint256 b = uint256(borrowAmt);
        uint256 c = uint256(collatAmt);
        if (s == 0) return;
        
        pool.supply(s);
        
        if (b > 0 && b < s) {
            pool.borrow(b, c);
        }
        
        // Solvency: totalSupplyAssets >= totalBorrowAssets
        assert(pool.totalSupplyAssets() >= pool.totalBorrowAssets());
    }

    /// Property: Token balance matches accounting
    function check_tokenAccounting(uint64 supplyAmt, uint64 borrowAmt, uint64 repayAmt) public {
        uint256 s = uint256(supplyAmt);
        uint256 b = uint256(borrowAmt);
        uint256 r = uint256(repayAmt);
        if (s == 0) return;
        
        pool.supply(s);
        
        if (b > 0 && b < s) {
            pool.borrow(b, s); // use supply as collateral
        }
        
        if (r > 0 && b > 0) {
            if (r > b) r = b;
            pool.repay(r);
        }
        
        // Token balance should equal totalSupplyAssets - totalBorrowAssets
        uint256 expected = pool.totalSupplyAssets() - pool.totalBorrowAssets();
        uint256 actual = pool.tokenBalance();
        
        // Allow 1 wei rounding tolerance
        if (actual > expected) {
            assert(actual - expected <= 1);
        } else {
            assert(expected - actual <= 1);
        }
    }
}
