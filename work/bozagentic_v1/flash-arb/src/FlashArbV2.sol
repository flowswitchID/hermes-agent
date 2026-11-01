// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title FlashArbV2 — BOZAGENTIC
/// @notice Flash loan arb: Aave → QuickSwap V2 (buy) → Uniswap V3 (sell)
interface IAavePool {
    function flashLoan(address,address[] calldata,uint256[] calldata,uint256[] calldata,address,bytes calldata,uint16) external;
}
interface IERC20 {
    function approve(address,uint256) external returns (bool);
    function transfer(address,uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}
interface IUniswapV3Router {
    struct ExactInputParams {
        bytes path;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }
    function exactInput(ExactInputParams calldata) external payable returns (uint256);
}
interface IV2Pair {
    function swap(uint256,uint256,address,bytes calldata) external;
    function getReserves() external view returns (uint112,uint112,uint32);
    function token0() external view returns (address);
}

contract FlashArbV2 {
    address constant AAVE = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant UNI = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant WETH = 0x4200000000000000000000000000000000000006;
    address constant QUICKSWAP_PAIR = 0x5a9Ad2BB92B0B3E5C571FDD5125114E04E02be1a;
    
    address immutable owner;
    uint256 private _profit;
    
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
        
        // Step 1: Transfer USDC to QuickSwap pair
        IERC20(USDC).transfer(QUICKSWAP_PAIR, amount);
        
        // Step 2: Call swap on QuickSwap pair
        // token0=WETH, token1=USDC. We send USDC, want WETH → amount0Out=wethOut, amount1Out=0
        (uint112 r0, uint112 r1,) = IV2Pair(QUICKSWAP_PAIR).getReserves();
        // r0 = WETH reserve, r1 = USDC reserve
        uint256 wethOut = (uint256(r0) * amount * 997) / (uint256(r1) * 1000 + amount * 997);
        require(wethOut > 0, "no WETH out");
        
        IV2Pair(QUICKSWAP_PAIR).swap(wethOut, 0, address(this), "");
        
        // Step 3: Sell WETH on Uniswap V3 for USDC
        uint256 wethBal = IERC20(WETH).balanceOf(address(this));
        IERC20(WETH).approve(UNI, wethBal);
        
        bytes memory path = abi.encodePacked(WETH, uint24(3000), USDC);
        uint256 usdcOut = IUniswapV3Router(UNI).exactInput(IUniswapV3Router.ExactInputParams({
            path: path,
            recipient: address(this),
            deadline: block.timestamp + 60,
            amountIn: wethBal,
            amountOutMinimum: 1
        }));
        
        // Step 4: Repay & profit
        if (usdcOut < repay) _profit = 0; else _profit = usdcOut - repay;
        if (_profit > 0) IERC20(USDC).transfer(owner, _profit);
        
        return true;
    }
}
