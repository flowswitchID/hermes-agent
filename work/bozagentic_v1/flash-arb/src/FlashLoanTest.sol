// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title FlashLoanTest — Minimal flash loan test
 * @notice Just borrows and repays — no swaps. Verifies Aave integration works.
 */

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

interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract FlashLoanTest is IFlashLoanReceiver {
    address constant AAVE_POOL = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant USDC      = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;

    event Log(string msg, uint256 val);

    function testFlashLoan(uint256 amount) external {
        address[] memory assets = new address[](1);
        assets[0] = USDC;

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;

        uint256[] memory modes = new uint256[](1);
        modes[0] = 0;

        IAavePool(AAVE_POOL).flashLoan(
            address(this), assets, amounts, modes, address(this), "", 0
        );
    }

    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        require(msg.sender == AAVE_POOL, "!pool");

        uint256 amount = amounts[0];
        uint256 premium = premiums[0];
        uint256 repayAmount = amount + premium;

        // Just check we received the funds
        uint256 bal = IERC20(USDC).balanceOf(address(this));
        emit Log("Received USDC", bal);
        emit Log("Need to repay", repayAmount);

        require(bal >= repayAmount, "!enough");

        // Approve and repay
        IERC20(USDC).approve(AAVE_POOL, repayAmount);

        emit Log("Repaid", repayAmount);
        return true;
    }

    function withdrawToken(address token, address to) external {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) {
            (bool ok,) = address(token).call(abi.encodeWithSignature("transfer(address,uint256)", to, bal));
            require(ok, "transfer failed");
        }
    }
}
