// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// BUG 1: Fee cap inconsistency (like CashbackRewards)
contract FeeBug {
    uint256 public cap = 1000;
    uint256 public distributed;
    uint256 public allocated;
    
    function allocate(uint256 amount) external {
        // Cap check uses distributed + allocated
        require(distributed + allocated + amount <= cap, "cap exceeded");
        allocated += amount;
    }
    
    function distribute(uint256 amount) external {
        // BUG: only checks distributed, ignores allocated
        require(distributed + amount <= cap, "cap exceeded");
        distributed += amount;
    }
}

// BUG 2: Missing health check
contract LendingBug {
    mapping(address => uint256) public debt;
    mapping(address => uint256) public collateral;
    
    function borrow(uint256 amount) external {
        // BUG: increases debt without checking collateralization
        debt[msg.sender] += amount;
        payable(msg.sender).transfer(amount);
    }
    
    function deposit() external payable {
        collateral[msg.sender] += msg.value;
    }
}

// BUG 3: Rounding direction mismatch
contract RoundingBug {
    uint256 public totalSupply;
    uint256 public totalAssets;
    
    function mulDivDown(uint256 x, uint256 y, uint256 d) internal pure returns (uint256) {
        return (x * y) / d;
    }
    function mulDivUp(uint256 x, uint256 y, uint256 d) internal pure returns (uint256) {
        return (x * y + d - 1) / d;
    }
    
    function deposit(uint256 assets) external returns (uint256 shares) {
        // Correct: round DOWN for deposit (user gets fewer shares)
        shares = mulDivDown(assets, totalSupply, totalAssets);
        totalSupply += shares;
        totalAssets += assets;
    }
    
    function withdraw(uint256 assets) external returns (uint256 shares) {
        // BUG: should round UP for withdraw (user should burn MORE shares)
        shares = mulDivDown(assets, totalSupply, totalAssets);
        totalSupply -= shares;
        totalAssets -= assets;
    }
}
