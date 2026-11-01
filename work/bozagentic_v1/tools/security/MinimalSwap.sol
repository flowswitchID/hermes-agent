// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

interface IWETH {
    function deposit() external payable;
    function approve(address, uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
}

interface IUniPool {
    function swap(address, bool, int256, uint160, bytes calldata) external returns (int256, int256);
    function slot0() external view returns (uint160, int24, uint16, uint16, uint16, uint8, bool);
}

/// @title MinimalSwap — 1 fungsi, 1 pool, no bullshit
/// @notice Swap ETH → USDC via Uniswap V3 pool langsung
contract MinimalSwap {
    address constant WETH = 0x4200000000000000000000000000000000000006;
    address constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    // WETH/USDC 0.30% pool di Base (verified: liquidity 3.2e19)
    address constant POOL = 0x6c561B446416E1A00E8E93E221854d6eA4171372;

    /// @notice Swap ETH → USDC. Kirim ETH via --value. USDC balik ke wallet lo.
    function swapETHtoUSDC(uint160 sqrtPriceLimit) external payable {
        require(msg.value > 0, "no ETH");

        // 1. Wrap ETH → WETH
        IWETH(WETH).deposit{value: msg.value}();

        // 2. Approve pool buat tarik WETH
        IWETH(WETH).approve(POOL, msg.value);

        // 3. Swap: zeroForOne=true (jual WETH/token0, beli USDC/token1)
        IUniPool(POOL).swap(
            msg.sender,     // USDC langsung ke wallet lo
            true,           // zeroForOne: WETH → USDC
            int256(msg.value),
            sqrtPriceLimit, // pakai slot0 - 1
            ""
        );

        // 4. Refund WETH sisa (kalau ada dust)
        uint256 leftover = IWETH(WETH).balanceOf(address(this));
        if (leftover > 0) IERC20(WETH).transfer(msg.sender, leftover);
    }

    /// @notice Callback — pool narik WETH dari kontrak ini
    function uniswapV3SwapCallback(int256 amount0Delta, int256, bytes calldata) external {
        require(msg.sender == POOL, "wrong pool");
        if (amount0Delta > 0) {
            IWETH(WETH).transfer(POOL, uint256(amount0Delta));
        }
    }

    /// @notice Cek harga WETH saat ini (dari slot0)
    function getPrice() external view returns (uint256 usdcPerWeth) {
        (uint160 sqrt,,,,,,) = IUniPool(POOL).slot0();
        usdcPerWeth = uint256(sqrt) * uint256(sqrt) * 1e12 / (2**192);
    }
}
