// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IAave {
    function flashLoanSimple(address,address,uint256,bytes calldata,uint16) external;
}
interface IV3Pool {
    function swap(address,bool,int256,uint160,bytes calldata) external returns(int256,int256);
    function slot0() external view returns(uint160);
}
interface IERC20 {
    function transfer(address,uint256) external returns(bool);
    function balanceOf(address) external view returns(uint256);
    function approve(address,uint256) external returns(bool);
}

contract FinalArb {
    address constant AAVE  = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant USDC  = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant WETH  = 0x4200000000000000000000000000000000000006;
    address constant P1    = 0x6c561B446416E1A00E8E93E221854d6eA4171372; // Uni 0.30% WETH/USDC
    address constant P2    = 0xd0b53D9277642d899DF5C87A3966A349A798F224; // Uni 0.05% WETH/USDC
    
    address public owner;
    event Arb(uint256 profit);
    modifier onlyOwner() { require(msg.sender == owner, "!"); _; }
    
    constructor() {
        owner = msg.sender;
        IERC20(USDC).approve(AAVE, type(uint256).max);
    }
    
    function execute(uint256 amount) external onlyOwner {
        IAave(AAVE).flashLoanSimple(address(this), USDC, amount, "", 0);
    }
    
    function executeOperation(address, uint256 amount, uint256 premium, address, bytes calldata) external returns(bool) {
        require(msg.sender == AAVE, "!aave");
        
        // Step 1: USDC -> WETH on 0.30% pool (t0=WETH, t1=USDC, zeroForOne=false = sell t1 for t0)
        IV3Pool(P1).swap(address(this), false, int256(amount), IV3Pool(P1).slot0() + 1, "");
        
        // Step 2: WETH -> USDC on 0.05% pool (zeroForOne=true = sell t0 for t1)
        uint256 w = IERC20(WETH).balanceOf(address(this));
        IV3Pool(P2).swap(address(this), true, int256(w), IV3Pool(P2).slot0() - 1, "");
        
        // Repay
        uint256 repay = amount + premium;
        IERC20(USDC).approve(AAVE, repay);
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        require(bal >= repay, "!repay");
        uint256 profit = bal - repay;
        if (profit > 0) IERC20(USDC).transfer(owner, profit);
        emit Arb(profit);
        return true;
    }
    
    function uniswapV3SwapCallback(int256 a0, int256 a1, bytes calldata) external {
        if (a0 > 0) IERC20(WETH).transfer(msg.sender, uint256(a0));
        if (a1 > 0) IERC20(USDC).transfer(msg.sender, uint256(a1));
    }
    
    function withdraw(address t) external onlyOwner {
        uint256 b = IERC20(t).balanceOf(address(this));
        if (b > 0) IERC20(t).transfer(owner, b);
    }
}
