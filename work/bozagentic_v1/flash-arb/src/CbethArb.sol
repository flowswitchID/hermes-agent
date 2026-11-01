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

contract CbethArb {
    address constant AAVE  = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant USDC  = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant WETH  = 0x4200000000000000000000000000000000000006;
    address constant CBETH = 0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22;
    
    // Pool addresses
    address constant WETH_USDC = 0x6c561B446416E1A00E8E93E221854d6eA4171372;  // Uni 0.30%: t0=WETH t1=USDC
    address constant QS_CBETH  = 0x74A4bF2cad1b172cDc82a5Da7130C7A59EB5460b;  // QuickSwap: t0=cbETH t1=WETH (CHEAP)
    address constant PS_CBETH  = 0xc0efC182479319ff258EcA420e2647cD82D3790c;  // PancakeSwap: t0=cbETH t1=WETH (EXPENSIVE)
    
    address public owner;
    event ArbResult(uint256 profit);
    
    modifier onlyOwner() { require(msg.sender == owner, "!owner"); _; }
    
    constructor() {
        owner = msg.sender;
        IERC20(USDC).approve(AAVE, type(uint256).max);
    }
    
    function execute(uint256 amount) external onlyOwner {
        IAavePool(AAVE).flashLoanSimple(address(this), USDC, amount, "", 0);
    }
    
    function executeOperation(address, uint256 amount, uint256 premium, address, bytes calldata) external returns (bool) {
        require(msg.sender == AAVE, "!pool");
        
        // Approve tokens for pools
        IERC20(CBETH).approve(PS_CBETH, type(uint256).max);
        
        // === STEP 1: USDC -> WETH (Uni 0.30%) ===
        // zeroForOne=false: sell token1(USDC) for token0(WETH)
        (uint160 sqrt,,,,,,) = IUniPool(WETH_USDC).slot0();
        IUniPool(WETH_USDC).swap(address(this), false, int256(amount), sqrt + 1, "");
        
        // === STEP 2: WETH -> cbETH (QuickSwap - CHEAP) ===
        // QuickSwap: t0=cbETH t1=WETH. zeroForOne=false: sell t1(WETH) for t0(cbETH)
        uint256 wethAmt = IERC20(WETH).balanceOf(address(this));
        (sqrt,,,,,,) = IUniPool(QS_CBETH).slot0();
        IUniPool(QS_CBETH).swap(address(this), false, int256(wethAmt), sqrt + 1, "");
        
        // === STEP 3: cbETH -> WETH (PancakeSwap - EXPENSIVE) ===
        // PancakeSwap: t0=cbETH t1=WETH. zeroForOne=true: sell t0(cbETH) for t1(WETH)
        uint256 cbethAmt = IERC20(CBETH).balanceOf(address(this));
        (sqrt,,,,,,) = IUniPool(PS_CBETH).slot0();
        IUniPool(PS_CBETH).swap(address(this), true, int256(cbethAmt), sqrt - 1, "");
        
        // === STEP 4: WETH -> USDC (Uni 0.30%) ===
        // zeroForOne=true: sell t0(WETH) for t1(USDC)
        uint256 wethBack = IERC20(WETH).balanceOf(address(this));
        (sqrt,,,,,,) = IUniPool(WETH_USDC).slot0();
        IUniPool(WETH_USDC).swap(address(this), true, int256(wethBack), sqrt - 1, "");
        
        // Repay Aave
        uint256 repayAmt = amount + premium;
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        require(bal >= repayAmt, "!repay");
        IERC20(USDC).approve(AAVE, repayAmt);
        
        uint256 profit = bal - repayAmt;
        if (profit > 0) IERC20(USDC).transfer(owner, profit);
        emit ArbResult(profit);
        return true;
    }
    
    function uniswapV3SwapCallback(int256 a0, int256 a1, bytes calldata) external {
        address pool = msg.sender;
        
        if (pool == WETH_USDC) {
            // token0=WETH, token1=USDC
            if (a0 > 0) IERC20(WETH).transfer(pool, uint256(a0));
            if (a1 > 0) IERC20(USDC).transfer(pool, uint256(a1));
        } else if (pool == QS_CBETH || pool == PS_CBETH) {
            // token0=cbETH, token1=WETH
            if (a0 > 0) IERC20(CBETH).transfer(pool, uint256(a0));
            if (a1 > 0) IERC20(WETH).transfer(pool, uint256(a1));
        }
    }
    
    function withdrawToken(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) IERC20(token).transfer(owner, bal);
    }
}
