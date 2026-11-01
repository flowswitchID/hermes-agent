// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title MinimalFlashArb — BOZAGENTIC
/// @notice Flash loan → triangular arb on Uniswap V3 only
interface IAavePool {
    function flashLoan(address,address[] calldata,uint256[] calldata,uint256[] calldata,address,bytes calldata,uint16) external;
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
interface IERC20 {
    function approve(address,uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
    function transfer(address,uint256) external returns (bool);
}

contract MinimalFlashArb {
    address constant AAVE = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant ROUTER = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant WETH = 0x4200000000000000000000000000000000000006;
    address constant cbETH = 0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22;
    
    address immutable owner;
    uint256 private _profit;
    
    constructor() { owner = msg.sender; IERC20(USDC).approve(ROUTER, type(uint256).max); }
    
    function execute(uint256 amount) external {
        address[] memory assets = new address[](1);
        assets[0] = USDC;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;
        uint256[] memory modes = new uint256[](1);
        modes[0] = 0;
        IAavePool(AAVE).flashLoan(address(this), assets, amounts, modes, address(this), "", 0);
    }
    
    function executeOperation(address[] calldata, uint256[] calldata amounts, uint256[] calldata premiums, address, bytes calldata) external returns (bool) {
        require(msg.sender == AAVE);
        _profit = 0;
        
        uint256 amount = amounts[0];
        uint256 premium = premiums[0];
        uint256 repay = amount + premium;
        
        // Path: USDC → WETH (0.05%) → USDC (0.30%) — fee tier arb
        bytes memory path = abi.encodePacked(
            USDC, uint24(500), WETH,
            uint24(3000), USDC
        );
        
        uint256 out = IUniswapV3Router(ROUTER).exactInput(IUniswapV3Router.ExactInputParams({
            path: path,
            recipient: address(this),
            deadline: block.timestamp + 60,
            amountIn: amount,
            amountOutMinimum: 1
        }));
        
        // Always repay. Profit is what's left after Aave pulls its share.
        if (out < repay) _profit = 0; else _profit = out - repay;
        if (_profit > 0) IERC20(USDC).transfer(owner, _profit);
        
        return true;
    }
    
    function withdraw() external {
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        if (bal > 0) IERC20(USDC).transfer(owner, bal);
    }
}
