// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Test.sol";

/// @notice Minimal ERC4626 vault for Halmos symbolic verification
/// @dev Implements core ERC4626 with virtual offset protection
contract ERC4626Vault {
    string public name = "Vault";
    string public symbol = "vTKN";
    uint8 public decimals = 18;

    address public asset;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    constructor(address _asset) {
        asset = _asset;
    }

    // ─── ERC20 ───────────────────────────────────────────────
    function transfer(address to, uint256 amount) external returns (bool) {
        balanceOf[msg.sender] -= amount;
        unchecked { balanceOf[to] += amount; }
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) {
            allowance[from][msg.sender] = allowed - amount;
        }
        balanceOf[from] -= amount;
        unchecked { balanceOf[to] += amount; }
        return true;
    }

    // ─── ERC4626 Core ────────────────────────────────────────
    function totalAssets() public view returns (uint256) {
        return IERC20(asset).balanceOf(address(this));
    }

    /// @dev Virtual offset: +1 to both supply and assets (OZ v4.9+ pattern)
    function convertToShares(uint256 assets) public view returns (uint256) {
        uint256 supply = totalSupply + 1e6;  // virtual offset
        uint256 assets_ = totalAssets() + 1e6;  // virtual offset
        return (assets * supply) / assets_;
    }

    function convertToAssets(uint256 shares) public view returns (uint256) {
        uint256 supply = totalSupply + 1e6;  // virtual offset
        uint256 assets_ = totalAssets() + 1e6;  // virtual offset
        return (shares * assets_) / supply;
    }

    function previewDeposit(uint256 assets) public view returns (uint256) {
        return convertToShares(assets);
    }

    function previewWithdraw(uint256 assets) public view returns (uint256) {
        uint256 supply = totalSupply + 1e6;
        uint256 assets_ = totalAssets() + 1e6;
        return (assets * supply + assets_ - 1) / assets_;  // round UP
    }

    function previewRedeem(uint256 shares) public view returns (uint256) {
        return convertToAssets(shares);
    }

    function deposit(uint256 assets, address receiver) external returns (uint256 shares) {
        shares = previewDeposit(assets);
        require(shares > 0, "ZERO_SHARES");
        IERC20(asset).transferFrom(msg.sender, address(this), assets);
        balanceOf[receiver] += shares;
        totalSupply += shares;
    }

    function mint(uint256 shares, address receiver) external returns (uint256 assets) {
        assets = previewMint(shares);
        IERC20(asset).transferFrom(msg.sender, address(this), assets);
        balanceOf[receiver] += shares;
        totalSupply += shares;
    }

    function previewMint(uint256 shares) public view returns (uint256) {
        uint256 supply = totalSupply + 1e6;
        uint256 assets_ = totalAssets() + 1e6;
        return (shares * assets_ + supply - 1) / supply;  // round UP
    }

    function withdraw(uint256 assets, address receiver, address owner) external returns (uint256 shares) {
        shares = previewWithdraw(assets);
        if (msg.sender != owner) {
            uint256 allowed = allowance[owner][msg.sender];
            if (allowed != type(uint256).max) {
                allowance[owner][msg.sender] = allowed - shares;
            }
        }
        balanceOf[owner] -= shares;
        totalSupply -= shares;
        IERC20(asset).transfer(receiver, assets);
    }

    function redeem(uint256 shares, address receiver, address owner) external returns (uint256 assets) {
        if (msg.sender != owner) {
            uint256 allowed = allowance[owner][msg.sender];
            if (allowed != type(uint256).max) {
                allowance[owner][msg.sender] = allowed - shares;
            }
        }
        assets = previewRedeem(shares);
        balanceOf[owner] -= shares;
        totalSupply -= shares;
        IERC20(asset).transfer(receiver, assets);
    }

    function maxDeposit(address) external pure returns (uint256) {
        return type(uint256).max;
    }

    function maxMint(address) external pure returns (uint256) {
        return type(uint256).max;
    }

    function maxWithdraw(address owner) external view returns (uint256) {
        return convertToAssets(balanceOf[owner]);
    }

    function maxRedeem(address owner) external view returns (uint256) {
        return balanceOf[owner];
    }
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
    function transferFrom(address, address, uint256) external returns (bool);
}

/// @notice Mock ERC20 for testing
contract MockERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        if (allowance[from][msg.sender] != type(uint256).max) {
            allowance[from][msg.sender] -= amount;
        }
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}
