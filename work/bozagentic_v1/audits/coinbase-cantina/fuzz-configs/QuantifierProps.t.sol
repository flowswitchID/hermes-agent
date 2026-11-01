// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QuantifierProps {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;
    
    function mint(address to, uint256 amount) external {
        balances[to] += amount;
        totalSupply += amount;
    }
    
    function burn(address from, uint256 amount) external {
        require(balances[from] >= amount, "insufficient");
        balances[from] -= amount;
        totalSupply -= amount;
    }
    
    function doTransfer(address from, address to, uint256 amount) external {
        require(balances[from] >= amount, "insufficient");
        balances[from] -= amount;
        balances[to] += amount;
    }
    
    function check_supply_consistency(address a, address b, uint256 amtA, uint256 amtB) external {
        if (amtA == 0 && amtB == 0) return;
        if (a == b) return;
        this.mint(a, amtA);
        this.mint(b, amtB);
        assert(totalSupply == balances[a] + balances[b]);
    }
    
    function check_transfer_preserves_supply(address a, address b, uint256 mintAmt, uint256 transferAmt) external {
        if (mintAmt == 0) return;
        if (a == b) return;
        if (transferAmt > mintAmt) transferAmt = mintAmt;
        this.mint(a, mintAmt);
        uint256 supplyBefore = totalSupply;
        this.doTransfer(a, b, transferAmt);
        assert(totalSupply == supplyBefore);
    }
    
    function check_burn_reduces_supply(address a, uint256 mintAmt, uint256 burnAmt) external {
        if (mintAmt == 0) return;
        if (burnAmt > mintAmt) burnAmt = mintAmt;
        this.mint(a, mintAmt);
        uint256 supplyBefore = totalSupply;
        this.burn(a, burnAmt);
        assert(totalSupply == supplyBefore - burnAmt);
    }
    
    function check_no_overburn(address a, uint256 amount) external {
        if (amount == 0) return;
        try this.burn(a, amount) {
            assert(false);
        } catch {}
    }
    
    function check_mint_burn_identity(address a, uint256 amount) external {
        if (amount == 0) return;
        uint256 supplyBefore = totalSupply;
        this.mint(a, amount);
        this.burn(a, amount);
        assert(totalSupply == supplyBefore);
        assert(balances[a] == 0);
    }
}
