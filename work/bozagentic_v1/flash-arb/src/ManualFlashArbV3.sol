// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IAavePool {
    function flashLoanSimple(address,address,uint256,bytes calldata,uint16) external;
}

interface IUniPool {
    function swap(address,bool,int256,uint160,bytes calldata) external returns (int256,int256);
    function slot0() external view returns (uint160,uint24,uint16,uint16,uint16,uint8,bool);
}

interface IERC20 {
    function approve(address,uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
    function transfer(address,uint256) external returns (bool);
}

contract ManualFlashArbV3 {
    address constant AAVE = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant WETH = 0x4200000000000000000000000000000000000006;
    
    address public owner;
    event ArbResult(uint256 borrowed, uint256 repaid, uint256 profit);
    
    modifier onlyOwner() { require(msg.sender == owner, "!owner"); _; }
    
    constructor() {
        owner = msg.sender;
        IERC20(USDC).approve(AAVE, type(uint256).max);
    }
    
    function execute(uint256 amount, address poolBuy, address poolSell) external onlyOwner {
        IAavePool(AAVE).flashLoanSimple(address(this), USDC, amount, abi.encode(poolBuy, poolSell), 0);
    }
    
    function executeOperation(address, uint256 amount, uint256 premium, address, bytes calldata params) external returns (bool) {
        require(msg.sender == AAVE, "!pool");
        
        (address poolBuy, address poolSell) = abi.decode(params, (address, address));
        IERC20(WETH).approve(poolSell, type(uint256).max);
        
        // Step 1: USDC -> WETH (buy at 1.00% pool)
        (uint160 sqrtBuy,,,,,,) = IUniPool(poolBuy).slot0();
        IUniPool(poolBuy).swap(address(this), false, int256(amount), sqrtBuy + 1, abi.encode(USDC, amount));
        
        // Step 2: WETH -> USDC (sell at 0.05% pool)
        uint256 wethBal = IERC20(WETH).balanceOf(address(this));
        (uint160 sqrtSell,,,,,,) = IUniPool(poolSell).slot0();
        IUniPool(poolSell).swap(address(this), true, int256(wethBal), sqrtSell - 1, abi.encode(WETH, wethBal));
        
        // Repay Aave
        uint256 repayAmount = amount + premium;
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        require(bal >= repayAmount, "!repay");
        IERC20(USDC).approve(AAVE, repayAmount);
        
        uint256 profit = bal - repayAmount;
        if (profit > 0) IERC20(USDC).transfer(owner, profit);
        
        emit ArbResult(amount, repayAmount, profit);
        return true;
    }
    
    function uniswapV3SwapCallback(int256 amount0Delta, int256 amount1Delta, bytes calldata) external {
        if (amount0Delta > 0) IERC20(WETH).transfer(msg.sender, uint256(amount0Delta));
        if (amount1Delta > 0) IERC20(USDC).transfer(msg.sender, uint256(amount1Delta));
    }
    
    function withdrawToken(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) IERC20(token).transfer(owner, bal);
    }
}
