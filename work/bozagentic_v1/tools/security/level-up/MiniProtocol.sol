// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @notice Simplified lending pool (like Morpho Blue)
contract MiniPool {
    uint256 constant WAD = 1e18;
    uint256 constant VIRTUAL_SHARES = 1e6;
    uint256 constant VIRTUAL_ASSETS = 1;

    uint256 public totalSupplyAssets;
    uint256 public totalSupplyShares;
    uint256 public totalBorrowAssets;
    uint256 public totalBorrowShares;
    mapping(address => uint256) public supplyShares;
    mapping(address => uint256) public borrowShares;
    mapping(address => uint256) public collateral;

    uint256 public tokenBalance; // simulated ERC20 balance

    function toSharesDown(uint256 a, uint256 ta, uint256 ts) internal pure returns (uint256) {
        return (a * (ts + VIRTUAL_SHARES)) / (ta + VIRTUAL_ASSETS);
    }
    function toAssetsUp(uint256 s, uint256 ta, uint256 ts) internal pure returns (uint256) {
        return (s * (ta + VIRTUAL_ASSETS) + (ts + VIRTUAL_SHARES - 1)) / (ts + VIRTUAL_SHARES);
    }
    function toAssetsDown(uint256 s, uint256 ta, uint256 ts) internal pure returns (uint256) {
        return (s * (ta + VIRTUAL_ASSETS)) / (ts + VIRTUAL_SHARES);
    }

    function supply(uint256 assets) external {
        require(assets > 0);
        uint256 shares = toSharesDown(assets, totalSupplyAssets, totalSupplyShares);
        supplyShares[msg.sender] += shares;
        totalSupplyShares += shares;
        totalSupplyAssets += assets;
        tokenBalance += assets;
    }

    function withdraw(uint256 assets) external {
        uint256 shares = toAssetsUp(assets, totalSupplyAssets, totalSupplyShares);
        // Actually need toSharesUp for withdraw
        shares = (assets * (totalSupplyShares + VIRTUAL_SHARES) + (totalSupplyAssets + VIRTUAL_ASSETS - 1)) / (totalSupplyAssets + VIRTUAL_ASSETS);
        require(shares <= supplyShares[msg.sender]);
        require(assets <= tokenBalance);
        supplyShares[msg.sender] -= shares;
        totalSupplyShares -= shares;
        totalSupplyAssets -= assets;
        tokenBalance -= assets;
    }

    function borrow(uint256 assets, uint256 collat) external {
        require(assets > 0);
        collateral[msg.sender] += collat;
        uint256 shares = (assets * (totalBorrowShares + VIRTUAL_SHARES) + (totalBorrowAssets + VIRTUAL_ASSETS - 1)) / (totalBorrowAssets + VIRTUAL_ASSETS);
        borrowShares[msg.sender] += shares;
        totalBorrowShares += shares;
        totalBorrowAssets += assets;
        tokenBalance -= assets;
    }

    function repay(uint256 assets) external {
        uint256 shares = toSharesDown(assets, totalBorrowAssets, totalBorrowShares);
        if (shares > borrowShares[msg.sender]) {
            shares = borrowShares[msg.sender];
            assets = toAssetsUp(shares, totalBorrowAssets, totalBorrowShares);
        }
        borrowShares[msg.sender] -= shares;
        totalBorrowShares -= shares;
        totalBorrowAssets = totalBorrowAssets > assets ? totalBorrowAssets - assets : 0;
        tokenBalance += assets;
    }

    function userSupplyAssets(address user) external view returns (uint256) {
        return toAssetsDown(supplyShares[user], totalSupplyAssets, totalSupplyShares);
    }
}

/// @notice Simplified vault that deposits into the pool (like MetaMorpho)
contract MiniVault {
    MiniPool public immutable pool;
    uint256 public totalShares;
    mapping(address => uint256) public balanceOf;
    uint256 public lastTotalAssets;

    constructor(address _pool) {
        pool = MiniPool(_pool);
    }

    function deposit(uint256 assets, address receiver) external {
        uint256 totalAssets = pool.totalSupplyAssets(); // simplified
        uint256 shares;
        if (totalShares == 0) {
            shares = assets;
        } else {
            shares = (assets * totalShares) / totalAssets;
        }
        require(shares > 0);

        // Vault supplies to pool on behalf of itself
        pool.supply(assets);

        balanceOf[receiver] += shares;
        totalShares += shares;
        lastTotalAssets = pool.totalSupplyAssets();
    }

    function vaultAssets() external view returns (uint256) {
        return pool.userSupplyAssets(address(this));
    }
}
