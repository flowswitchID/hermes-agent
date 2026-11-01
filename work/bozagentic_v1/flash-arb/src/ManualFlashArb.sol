// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title BOZAGENTIC — Manual Pool Flash Loan Arb
 * @notice SWAP langsung di pool Uniswap V3.
 *          Gak perlu API, gak perlu Permit2, gak perlu signature.
 * 
 * Flow:
 * 1. Flash loan USDC dari Aave
 * 2. Di callback:
 *    a. Swap USDC → WETH di Pool A (misal: 0.30%)
 *    b. Swap WETH → USDC di Pool B (misal: 0.05%)  
 *    c. Kalau hasil > pinjaman + fee = profit ✅
 * 3. Bayar Aave
 * 4. Profit ke owner
 */

interface IAavePool {
    function flashLoanSimple(address,address,uint256,bytes calldata,uint16) external;
}

interface IUniswapV3Pool {
    function swap(address,bool,int256,uint160,bytes calldata) external returns (int256,int256);
    function slot0() external view returns (uint160, uint24, uint16, uint16, uint16, uint8, bool);
}

interface IERC20 {
    function approve(address,uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
    function transfer(address,uint256) external returns (bool);
}

contract ManualFlashArb {
    address constant AAVE = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant WETH = 0x4200000000000000000000000000000000000006;
    
    // MIN_SQRT_RATIO + 1 for zeroForOne=true
    // MAX_SQRT_RATIO - 1 for zeroForOne=false  
    uint160 constant MIN_SQRT = 4295128739;
    uint160 constant MAX_SQRT = 1461446703485210103287273052203988822378723970341;
    
    address public owner;
    event ArbResult(uint256 borrowed, uint256 repaid, uint256 profit);
    
    modifier onlyOwner() { require(msg.sender == owner, "!owner"); _; }
    
    constructor() {
        owner = msg.sender;
        IERC20(USDC).approve(AAVE, type(uint256).max);
    }
    
    /**
     * @notice Execute flash loan arb
     * @param amount USDC to borrow (6 decimals)
     * @param poolBuy Pool untuk beli WETH (USDC->WETH, zeroForOne=false)
     * @param poolSell Pool untuk jual WETH (WETH->USDC, zeroForOne=true)
     */
    function execute(uint256 amount, address poolBuy, address poolSell) external onlyOwner {
        bytes memory params = abi.encode(poolBuy, poolSell);
        IAavePool(AAVE).flashLoanSimple(address(this), USDC, amount, params, 0);
    }
    
    function executeOperation(
        address, uint256 amount, uint256 premium,
        address, bytes calldata params
    ) external returns (bool) {
        require(msg.sender == AAVE, "!pool");
        
        uint256 repayAmount = amount + premium;
        
        (address poolBuy, address poolSell) = abi.decode(params, (address, address));
        
        // Get current sqrt price to set limits correctly
        (uint160 sqrtCurrent, , , , , , ) = IUniswapV3Pool(poolBuy).slot0();
        
        IERC20(WETH).approve(poolSell, type(uint256).max);
        
        // Step 1: Beli WETH di poolBuy (zeroForOne=false)
        // sqrtPriceLimit must be > current sqrt
        IUniswapV3Pool(poolBuy).swap(
            address(this),
            false,
            int256(amount),
            sqrtCurrent + 1,  // just above current price
            abi.encode(USDC, amount)
        );
        
        // Step 2: Jual WETH di poolSell (zeroForOne=true)
        uint256 wethBal = IERC20(WETH).balanceOf(address(this));
        (sqrtCurrent, , , , , , ) = IUniswapV3Pool(poolSell).slot0();
        
        IUniswapV3Pool(poolSell).swap(
            address(this),
            true,
            int256(wethBal),
            sqrtCurrent - 1,  // just below current price
            abi.encode(WETH, wethBal)
        );
        
        // Bayar Aave
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        require(bal >= repayAmount, "!repay");
        IERC20(USDC).approve(AAVE, repayAmount);
        
        uint256 profit = bal - repayAmount;
        if (profit > 0) IERC20(USDC).transfer(owner, profit);
        
        emit ArbResult(amount, repayAmount, profit);
        return true;
    }
    
    // Callback dari pool swap — kirim token yang diminta
    function uniswapV3SwapCallback(int256 amount0Delta, int256 amount1Delta, bytes calldata data) external {
        (address token, uint256 amount) = abi.decode(data, (address, uint256));
        
        // amount0Delta = token0 (WETH), amount1Delta = token1 (USDC)
        // Mana yang positif = token yang harus kita kirim
        if (amount0Delta > 0) {
            // Kita harus kirim WETH (token0)
            IERC20(WETH).transfer(msg.sender, uint256(amount0Delta));
        }
        if (amount1Delta > 0) {
            // Kita harus kirim USDC (token1)
            IERC20(USDC).transfer(msg.sender, uint256(amount1Delta));
        }
    }
    
    function withdrawToken(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) IERC20(token).transfer(owner, bal);
    }
    
    function setOwner(address o) external onlyOwner { owner = o; }
}
