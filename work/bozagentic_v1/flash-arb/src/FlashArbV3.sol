// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title FlashArbV3 — BOZAGENTIC
/// @notice Flash loan: Aave → Aerodrome V2 pool (buy) → Uniswap V3 (sell)
interface IAavePool {
    function flashLoan(address,address[] calldata,uint256[] calldata,uint256[] calldata,address,bytes calldata,uint16) external;
}
interface IERC20 {
    function approve(address,uint256) external returns (bool);
    function transfer(address,uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}
interface IUniswapV3 {
    struct ExactInputParams {
        bytes path;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }
    function exactInput(ExactInputParams calldata) external payable returns (uint256);
}
interface IV2Pool {
    function swap(uint256,uint256,address,bytes calldata) external;
    function token0() external view returns (address);
    function token1() external view returns (address);
}

contract FlashArbV3 {
    address constant AAVE = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant UNI = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant WETH = 0x4200000000000000000000000000000000000006;
    address constant AERO_POOL = 0xb2cc224c1c9feE385f8ad6a55b4d94E92359DC59;
    
    address immutable owner;
    
    constructor() { owner = msg.sender; IERC20(USDC).approve(UNI, type(uint256).max); }
    
    function execute(uint256 usdcAmount) external {
        address[] memory a = new address[](1); a[0] = USDC;
        uint256[] memory am = new uint256[](1); am[0] = usdcAmount;
        uint256[] memory mo = new uint256[](1); mo[0] = 0;
        IAavePool(AAVE).flashLoan(address(this), a, am, mo, address(this), "", 0);
    }
    
    function executeOperation(address[] calldata, uint256[] calldata amounts, uint256[] calldata premiums, address, bytes calldata) external returns (bool) {
        require(msg.sender == AAVE);
        
        uint256 amount = amounts[0];
        uint256 repay = amount + premiums[0];
        
        // STEP 1: Swap USDC → WETH on Aerodrome V2 pool
        IV2Pool pool = IV2Pool(AERO_POOL);
        address token0 = pool.token0(); // WETH
        address token1 = pool.token1(); // USDC
        
        // Get reserves BEFORE transferring tokens
        uint256 r0 = IERC20(token0).balanceOf(AERO_POOL); // WETH reserve
        uint256 r1 = IERC20(token1).balanceOf(AERO_POOL); // USDC reserve
        
        // For V2: we send token1 (USDC), get token0 (WETH) out
        // amount0Out = (r0 * amount * 997) / (r1 * 1000 + amount * 997)
        uint256 wethOut = (r0 * amount * 997) / (r1 * 1000 + amount * 997);
        require(wethOut > 0, "no WETH");
        
        // Transfer USDC to pool, then call swap
        IERC20(USDC).transfer(AERO_POOL, amount);
        pool.swap(wethOut, 0, address(this), "");
        
        // STEP 2: Sell WETH on Uniswap V3 for USDC
        uint256 wethBal = IERC20(WETH).balanceOf(address(this));
        require(wethBal > 0, "no WETH bal");
        IERC20(WETH).approve(UNI, wethBal);
        
        bytes memory path = abi.encodePacked(WETH, uint24(3000), USDC);
        uint256 usdcOut = IUniswapV3(UNI).exactInput(IUniswapV3.ExactInputParams({
            path: path,
            recipient: address(this),
            deadline: block.timestamp + 60,
            amountIn: wethBal,
            amountOutMinimum: 1
        }));
        
        // STEP 3: Repay & keep profit
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        require(bal >= repay, "!repay");
        
        uint256 profit = bal - repay;
        if (profit > 0) IERC20(USDC).transfer(owner, profit);
        
        return true;
    }
    
    function withdraw() external {
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        if (bal > 0) IERC20(USDC).transfer(owner, bal);
    }
}
