// SPDX-License-Identifier: GPL-3.0-only
pragma solidity ^0.8.23;

import {AccessControlEnumerable} from "@openzeppelin/contracts/access/extensions/AccessControlEnumerable.sol";
import {IERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Permit.sol";
import {IERC20, SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {ConfigChanged} from "echo/interfaces/PlatformEvents.sol";
import {Versioned} from "echo/Versioned.sol";
import {Deal, DealSignatureLib} from "./Deal.sol";

/// @title ERC20FundingConduit
/// @notice A funding conduit that allows users to fund a deal by signing an ERC20 Permit and sending the signed permit to the platform, which will execute the funding transaction on the user's behalf.
contract ERC20FundingConduit is AccessControlEnumerable, Versioned(2, 0, 0) {
    using SafeERC20 for IERC20;

    /// @notice Thrown when the fee amount is too large.
    error FeeAmountTooLarge(uint256 feeAmount, uint256 maxFee);

    /// @notice Emitted when a user paid some fees.
    event FeesPaid(address indexed user, uint256 amount);

    /// @notice The role allowed to manage the deal (e.g. the platform provider, or deal lead)
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");

    /// @notice The role allowed to execute the users funding transactions (i.e. the platform's backend).
    bytes32 public constant TX_SENDER_ROLE = keccak256("TX_SENDER_ROLE");

    /// @notice The address to which fees are transferred.
    address public feesReceiver;

    constructor(address admin, address manager, address txSender, address feeReceiver) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MANAGER_ROLE, manager);

        _setRoleAdmin(TX_SENDER_ROLE, MANAGER_ROLE);
        _grantRole(TX_SENDER_ROLE, txSender);

        feesReceiver = feeReceiver;
    }

    /// @notice Funds a deal on behalf of a user using an ERC20 permit.
    /// @dev The contract redeems an ERC20 permit to pull the corresponding funds from the user.
    /// NB: the amount of fees and which deal will be funded is not explicitly signed by the user and the user trusts the platform to do the routing correctly.
    function fundUsingPermit(
        address user,
        uint256 feesAmount,
        Deal deal,
        uint256 fundingAmount,
        DealSignatureLib.DealFundingPermit calldata fundingPermit,
        bytes calldata fundingPermitSignature,
        uint256 erc20PermitDeadline,
        bytes calldata erc20PermitSignature
    ) external onlyRole(TX_SENDER_ROLE) {
        IERC20 token = deal.token();
        IERC20Permit ptoken = IERC20Permit(address(token));
        ptoken.permit({
            owner: user,
            spender: address(this),
            value: fundingAmount + feesAmount,
            deadline: erc20PermitDeadline,
            r: bytes32(erc20PermitSignature[0:32]),
            s: bytes32(erc20PermitSignature[32:64]),
            v: uint8(bytes1(erc20PermitSignature[64]))
        });

        _fundUsingApproval({
            user: user,
            feesAmount: feesAmount,
            deal: deal,
            fundingAmount: fundingAmount,
            fundingPermit: fundingPermit,
            fundingPermitSignature: fundingPermitSignature
        });
    }

    /// @notice Funds a deal on behalf of a user, using an existing ERC20 approval.
    /// @dev The user must have approved this contract explicitly to spend the funding amount.
    /// NB: the amount of fees and which deal will be funded is not explicitly signed by the user and the user trusts the platform to do the routing correctly.
    function fundUsingApproval(
        address user,
        uint256 feesAmount,
        Deal deal,
        uint256 fundingAmount,
        DealSignatureLib.DealFundingPermit calldata fundingPermit,
        bytes calldata fundingPermitSignature
    ) external onlyRole(TX_SENDER_ROLE) {
        _fundUsingApproval({
            user: user,
            feesAmount: feesAmount,
            deal: deal,
            fundingAmount: fundingAmount,
            fundingPermit: fundingPermit,
            fundingPermitSignature: fundingPermitSignature
        });
    }

    function _fundUsingApproval(
        address user,
        uint256 feesAmount,
        Deal deal,
        uint256 fundingAmount,
        DealSignatureLib.DealFundingPermit calldata fundingPermit,
        bytes calldata fundingPermitSignature
    ) internal {
        if (feesAmount > _maxFee()) {
            revert FeeAmountTooLarge({feeAmount: feesAmount, maxFee: _maxFee()});
        }

        IERC20 token = deal.token();
        emit FeesPaid(user, feesAmount);
        token.safeTransferFrom(user, feesReceiver, feesAmount);
        token.safeTransferFrom(user, address(this), fundingAmount);
        token.approve(address(deal), fundingAmount);

        deal.fundFromConduit({
            user: user,
            amount: fundingAmount,
            fundingPermit: fundingPermit,
            signature: fundingPermitSignature
        });
    }

    function _maxFee() internal pure virtual returns (uint256) {
        // Hardcoding a max fee of 100$ for now, which commonly uses 6 decimals (e.g. USDC, USDT)
        return 100 * 1e6;
    }

    /// @notice Sets the address to which fees are transferred.
    function setFeesReceiver(address newReceiver) external onlyRole(MANAGER_ROLE) {
        feesReceiver = newReceiver;
        emit ConfigChanged(this.setFeesReceiver.selector, "setFeesReceiver(address)", abi.encode(newReceiver));
    }
}
