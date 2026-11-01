// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

// Single mock that acts as WETH, collToken, PriceFeed, InterestRouter
// Deployed BEFORE the harness so its code is available for callbacks
contract MockAll {
    // ERC20
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;
    string public name = "Mock WETH";
    string public symbol = "WETH";
    uint8 public decimals = 18;
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }
    
    function transfer(address to, uint256 amount) external returns (bool) {
        if (balanceOf[msg.sender] >= amount) {
            balanceOf[msg.sender] -= amount;
            balanceOf[to] += amount;
        }
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        if (allowance[from][msg.sender] < type(uint256).max) {
            if (allowance[from][msg.sender] >= amount) allowance[from][msg.sender] -= amount;
        }
        if (balanceOf[from] >= amount) {
            balanceOf[from] -= amount;
            balanceOf[to] += amount;
        }
        return true;
    }
    
    // IWETH
    function deposit() external payable {
        balanceOf[msg.sender] += msg.value;
        totalSupply += msg.value;
    }
    
    function withdraw(uint256 amount) external {
        if (balanceOf[msg.sender] >= amount) {
            balanceOf[msg.sender] -= amount;
            totalSupply -= amount;
        }
    }
    
    // IPriceFeed
    function fetchPrice() external pure returns (uint256, bool) {
        return (2000e18, false);
    }
    
    function fetchRedemptionPrice() external pure returns (uint256, bool) {
        return (2000e18, false);
    }
    
    // IInterestRouter
    function receiveBold() external {}
    
    // Mint helper for testing
    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
    }
    
    receive() external payable {
        balanceOf[msg.sender] += msg.value;
        totalSupply += msg.value;
    }
}
