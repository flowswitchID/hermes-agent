// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

/// @title MiniVault — ERC4626-like vault
contract MiniVault {
    mapping(address => uint256) public shares;
    uint256 public totalShares;
    uint256 public totalAssets;
    
    event Deposit(address indexed user, uint256 assets, uint256 sharesMinted);
    event Withdraw(address indexed user, uint256 assets, uint256 sharesBurned);
    
    function deposit(uint256 assets) external returns (uint256 sharesMinted) {
        require(assets > 0, "zero");
        // First depositor: 1:1
        if (totalShares == 0) {
            sharesMinted = assets;
        } else {
            sharesMinted = (assets * totalShares) / totalAssets;
        }
        require(sharesMinted > 0, "zero shares");
        shares[msg.sender] += sharesMinted;
        totalShares += sharesMinted;
        totalAssets += assets;
        emit Deposit(msg.sender, assets, sharesMinted);
    }
    
    function withdraw(uint256 sharesToBurn) external returns (uint256 assetsOut) {
        require(sharesToBurn > 0 && sharesToBurn <= shares[msg.sender], "bad");
        assetsOut = (sharesToBurn * totalAssets) / totalShares;
        shares[msg.sender] -= sharesToBurn;
        totalShares -= sharesToBurn;
        totalAssets -= assetsOut;
        emit Withdraw(msg.sender, assetsOut, sharesToBurn);
    }
    
    // Simulate donation (direct token transfer)
    function simulateDonation(uint256 amount) external {
        totalAssets += amount;
    }
    
    function previewWithdraw(uint256 sharesToBurn) external view returns (uint256) {
        if (totalShares == 0) return 0;
        return (sharesToBurn * totalAssets) / totalShares;
    }
}

/// @title MiniLender — borrows against vault collateral
contract MiniLender {
    MiniVault public immutable vault;
    
    struct Position {
        uint256 collateralShares;
        uint256 debt;
    }
    
    mapping(address => Position) public positions;
    uint256 public totalDebt;
    uint256 public constant LTV = 7500; // 75% in bps
    uint256 public constant LIQUIDATION_THRESHOLD = 8000; // 80%
    uint256 public constant LIQUIDATION_PENALTY = 500; // 5%
    
    constructor(address _vault) {
        vault = MiniVault(_vault);
    }
    
    function borrow(uint256 collateralShares, uint256 amount) external {
        require(collateralShares > 0 && amount > 0, "zero");
        // Transfer shares from user to this contract as collateral
        // Simplified: just track
        Position storage pos = positions[msg.sender];
        pos.collateralShares += collateralShares;
        
        // Check LTV
        uint256 collateralValue = vault.previewWithdraw(pos.collateralShares);
        uint256 maxBorrow = (collateralValue * LTV) / 10000;
        require(pos.debt + amount <= maxBorrow, "LTV exceeded");
        
        pos.debt += amount;
        totalDebt += amount;
    }
    
    function repay(uint256 amount) external {
        Position storage pos = positions[msg.sender];
        require(amount <= pos.debt, "overpay");
        pos.debt -= amount;
        totalDebt -= amount;
    }
    
    function liquidate(address user) external {
        Position storage pos = positions[user];
        require(pos.debt > 0, "no debt");
        
        uint256 collateralValue = vault.previewWithdraw(pos.collateralShares);
        uint256 healthRatio = (collateralValue * 10000) / pos.debt;
        require(healthRatio < LIQUIDATION_THRESHOLD, "healthy");
        
        // Liquidator pays debt, gets collateral + penalty
        uint256 penaltyAmount = (pos.debt * LIQUIDATION_PENALTY) / 10000;
        uint256 sharesToSeize = pos.collateralShares; // simplified: seize all
        
        totalDebt -= pos.debt;
        pos.debt = 0;
        pos.collateralShares = 0;
    }
    
    function getHealthRatio(address user) external view returns (uint256) {
        Position storage pos = positions[user];
        if (pos.debt == 0) return type(uint256).max;
        uint256 collateralValue = vault.previewWithdraw(pos.collateralShares);
        return (collateralValue * 10000) / pos.debt;
    }
}
