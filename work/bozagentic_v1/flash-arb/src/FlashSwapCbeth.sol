// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IUniPool {
    function swap(address,bool,int256,uint160,bytes calldata) external returns (int256,int256);
    function slot0() external view returns (uint160,uint24,uint16,uint16,uint16,uint8,bool);
}
interface IERC20 {
    function transfer(address,uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

contract FlashSwapCbeth {
    address constant CBETH = 0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22;
    address constant WETH  = 0x4200000000000000000000000000000000000006;
    address constant CHEAP = 0x74A4bF2cad1b172cDc82a5Da7130C7A59EB5460b;  // QuickSwap: t0=cbETH t1=WETH (murah)
    address constant DEAR  = 0xc0efC182479319ff258EcA420e2647cD82D3790c;  // PancakeSwap: t0=cbETH t1=WETH (mahal)
    
    uint160 constant MIN_SQRT = 4295128739;
    uint160 constant MAX_SQRT = 1461446703485210103287273052203988822378723970341;
    
    address public owner;
    event Profit(uint256 wethAmt);
    modifier onlyOwner() { require(msg.sender == owner, "!"); _; }
    constructor() { owner = msg.sender; }
    
    // Pinjam cbETH dari QuickSwap → jual mahal di PancakeSwap → bayar QuickSwap → profit WETH
    function execute(uint256 cbethAmount) external onlyOwner {
        // Borrow cbETH via flash swap (exact output)
        // zeroForOne=false: receive t0(cbETH) | pay t1(WETH)
        IUniPool(CHEAP).swap(address(this), false, -int256(cbethAmount), MAX_SQRT, "");
        
        uint256 profit = IERC20(WETH).balanceOf(address(this));
        if (profit > 0) {
            IERC20(WETH).transfer(owner, profit);
            emit Profit(profit);
        }
    }
    
    function uniswapV3SwapCallback(int256 a0, int256 a1, bytes calldata) external {
        // QuickSwap (CHEAP) flash swap: kita terima cbETH, bayar WETH
        uint256 owedWeth = uint256(a1);
        uint256 cbethBal = IERC20(CBETH).balanceOf(address(this));
        
        // Jual cbETH di PancakeSwap (harga mahal)
        IUniPool(DEAR).swap(address(this), true, int256(cbethBal), MIN_SQRT, "");
        
        // Bayar hutang WETH
        IERC20(WETH).transfer(msg.sender, owedWeth);
    }
    
    // PancakeSwap pake callback ini (selector 0x23a69e75)
    function pancakeV3SwapCallback(int256 a0, int256 a1, bytes calldata) external {
        if (msg.sender == DEAR) {
            // Kirim cbETH ke PancakeSwap
            if (a0 > 0) IERC20(CBETH).transfer(msg.sender, uint256(a0));
        }
    }
    
    function withdraw(address t) external onlyOwner {
        uint256 b = IERC20(t).balanceOf(address(this));
        if (b > 0) IERC20(t).transfer(owner, b);
    }
}
