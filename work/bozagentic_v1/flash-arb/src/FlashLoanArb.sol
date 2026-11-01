// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title FlashLoanArb — BOZAGENTIC by 0x_spectrum
 * @notice Flash loan arbitrage on Base chain via Aave V3
 * @dev Buy token on cheap DEX, sell on expensive DEX, repay Aave, keep profit
 */

// === Aave V3 Interfaces ===
interface IAavePool {
    function flashLoan(
        address receiver,
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata interestRateModes,
        address onBehalfOf,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

interface IFlashLoanReceiver {
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}

// === ERC20 ===
interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

// === Uniswap V3 Router ===
interface IUniswapV3Router {
    struct ExactInputParams {
        bytes path;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }
    function exactInput(ExactInputParams calldata params) external payable returns (uint256 amountOut);
}

// === Aerodrome (Velodrome) Router ===
interface IAerodromeRouter {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

contract FlashLoanArb is IFlashLoanReceiver {
    address public owner;

    // Constants — Base Chain
    address constant AAVE_POOL       = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant USDC            = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant AERO            = 0x940181a94A35A4569E4529A3CDfB74e38FD98631;
    address constant WETH            = 0x4200000000000000000000000000000000000006;
    address constant UNISWAP_V3_ROUTER = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address constant AERODROME_ROUTER  = 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43;

    event Log(string msg, uint256 val);
    event ArbResult(uint256 borrowed, uint256 repaid, uint256 profit);

    modifier onlyOwner() {
        require(msg.sender == owner, "!owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        IERC20(USDC).approve(UNISWAP_V3_ROUTER, type(uint256).max);
        IERC20(USDC).approve(AERODROME_ROUTER, type(uint256).max);
        IERC20(AERO).approve(UNISWAP_V3_ROUTER, type(uint256).max);
        IERC20(AERO).approve(AERODROME_ROUTER, type(uint256).max);
        IERC20(WETH).approve(UNISWAP_V3_ROUTER, type(uint256).max);
    }

    /// @notice Execute flash loan
    /// @param amount USDC to borrow (6 decimals, e.g. 1000000 = $1)
    /// @param path 0 = Aerodrome buy → Uniswap sell
    ///             1 = Uniswap buy → Aerodrome sell
    function execute(uint256 amount, uint8 path) external onlyOwner {
        bytes memory params = abi.encode(path);

        address[] memory assets = new address[](1);
        assets[0] = USDC;

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;

        uint256[] memory modes = new uint256[](1);
        modes[0] = 0; // 0 = no debt (flash loan), 1 = stable, 2 = variable

        IAavePool(AAVE_POOL).flashLoan(
            address(this),
            assets,
            amounts,
            modes,
            address(this),
            params,
            0
        );
    }

    /// @notice Aave V3 callback — all arb logic happens here
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        require(msg.sender == AAVE_POOL, "!pool");
        require(assets[0] == USDC, "!USDC");

        uint8 path = abi.decode(params, (uint8));
        uint256 amount = amounts[0];
        uint256 premium = premiums[0];
        uint256 repayAmount = amount + premium;

        if (path == 0) {
            // Buy AERO cheap on Aerodrome (USDC → WETH → AERO)
            _swapAerodrome(USDC, amount, WETH, AERO);
            // Sell AERO on Uniswap V3 (AERO → USDC)
            uint256 aeroBal = IERC20(AERO).balanceOf(address(this));
            require(aeroBal > 0, "no AERO bought");
            _swapUniswap(AERO, aeroBal, USDC);
        } else {
            // Buy AERO on Uniswap V3 (USDC → AERO)
            _swapUniswap(USDC, amount, AERO);
            // Sell AERO on Aerodrome (AERO → WETH → USDC)
            uint256 aeroBal2 = IERC20(AERO).balanceOf(address(this));
            require(aeroBal2 > 0, "no AERO bought");
            _swapAerodrome(AERO, aeroBal2, WETH, USDC);
        }

        // Repay Aave loan
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        require(bal >= repayAmount, "!repay");

        IERC20(USDC).approve(AAVE_POOL, repayAmount);

        uint256 profit = bal - repayAmount;
        if (profit > 0) {
            IERC20(USDC).transfer(owner, profit);
        }

        emit ArbResult(amount, repayAmount, profit);
        return true;
    }

    /// @notice Swap on Aerodrome via router (USDC → WETH → tokenOut)
    function _swapAerodrome(address tokenIn, uint256 amountIn, address intermediate, address tokenOut) internal {
        IERC20(tokenIn).approve(AERODROME_ROUTER, amountIn);

        address[] memory path = new address[](3);
        path[0] = tokenIn;
        path[1] = intermediate;
        path[2] = tokenOut;

        IAerodromeRouter(AERODROME_ROUTER).swapExactTokensForTokens(
            amountIn, 0, path, address(this), block.timestamp + 60
        );
    }

    /// @notice Swap on Uniswap V3 (tokenIn -> tokenOut)
    function _swapUniswap(address tokenIn, uint256 amountIn, address tokenOut) internal {
        IERC20(tokenIn).approve(UNISWAP_V3_ROUTER, amountIn);

        bytes memory swapPath = abi.encodePacked(tokenIn, uint24(3000), tokenOut);

        IUniswapV3Router(UNISWAP_V3_ROUTER).exactInput(
            IUniswapV3Router.ExactInputParams({
                path: swapPath,
                recipient: address(this),
                deadline: block.timestamp + 60,
                amountIn: amountIn,
                amountOutMinimum: 1
            })
        );
    }

    /// @notice Check contract balance
    function getBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }

    /// @notice Withdraw stuck tokens
    function withdrawToken(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) IERC20(token).transfer(owner, bal);
    }

    receive() external payable {}
    function withdrawETH() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }
}
