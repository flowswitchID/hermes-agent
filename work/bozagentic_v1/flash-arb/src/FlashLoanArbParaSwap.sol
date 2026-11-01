// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title FlashLoanArbParaSwap — BOZAGENTIC
 * @notice Flash loan + dual-swap via ParaSwap (cross-DEX arb)
 * 
 * Flow:
 * 1. Flash loan USDC from Aave
 * 2. Swap USDC → WETH via ParaSwap (best price across ALL DEXs)
 * 3. Approve WETH for ParaSwap Proxy
 * 4. Swap WETH → USDC via ParaSwap (best price across ALL DEXs)
 * 5. Repay Aave + premium → profit!
 */

interface IAavePool {
    function flashLoan(address,address[] calldata,uint256[] calldata,uint256[] calldata,address,bytes calldata,uint16) external;
}
interface IERC20 {
    function approve(address,uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
    function transfer(address,uint256) external returns (bool);
}

contract FlashLoanArbParaSwap {
    address constant AAVE = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant WETH = 0x4200000000000000000000000000000000000006;
    address constant PROXY = 0x93aAAe79a53759cD164340E4C8766E4Db5331cD7;
    
    address public owner;
    
    event ArbResult(uint256 borrowed, uint256 repaid, uint256 profit);
    
    modifier onlyOwner() { require(msg.sender == owner, "!owner"); _; }
    
    constructor() {
        owner = msg.sender;
        IERC20(USDC).approve(PROXY, type(uint256).max);
        IERC20(WETH).approve(PROXY, type(uint256).max);
    }
    
    /**
     * @notice Execute flash loan arbitrage
     * @param amount USDC to borrow (6 decimals)
     * @param swap1Target ParaSwap contract for first swap
     * @param swap1Data Calldata for first swap (USDC -> WETH)
     * @param swap2Target ParaSwap contract for second swap  
     * @param swap2Data Calldata for second swap (WETH -> USDC)
     */
    function execute(
        uint256 amount,
        address swap1Target,
        bytes calldata swap1Data,
        address swap2Target,
        bytes calldata swap2Data
    ) external onlyOwner {
        bytes memory params = abi.encode(swap1Target, swap1Data, swap2Target, swap2Data);
        
        address[] memory assets = new address[](1);
        assets[0] = USDC;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;
        uint256[] memory modes = new uint256[](1);
        modes[0] = 0;
        
        IAavePool(AAVE).flashLoan(address(this), assets, amounts, modes, address(this), params, 0);
    }
    
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        require(msg.sender == AAVE, "!pool");
        
        uint256 amount = amounts[0];
        uint256 repayAmount = amount + premiums[0];
        
        // Decode params
        (address t1, bytes memory d1, address t2, bytes memory d2) = 
            abi.decode(params, (address, bytes, address, bytes));
        
        // Step 1: Swap USDC -> WETH via ParaSwap
        (bool ok1,) = t1.call(d1);
        require(ok1, "Swap1 failed");
        
        // Step 2: Swap WETH -> USDC via ParaSwap
        (bool ok2,) = t2.call(d2);
        require(ok2, "Swap2 failed");
        
        // Repay Aave
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        require(bal >= repayAmount, "!repay");
        IERC20(USDC).approve(AAVE, repayAmount);
        
        uint256 profit = bal - repayAmount;
        if (profit > 0) IERC20(USDC).transfer(owner, profit);
        
        emit ArbResult(amount, repayAmount, profit);
        return true;
    }
    
    function withdrawToken(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) IERC20(token).transfer(owner, bal);
    }
    
    function setOwner(address o) external onlyOwner { owner = o; }
    receive() external payable {}
}
