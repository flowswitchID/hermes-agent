// SPDX-License-Identifier: GPL-3.0-only
pragma solidity ^0.8.23;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {AccessControlEnumerable} from "@openzeppelin/contracts/access/extensions/AccessControlEnumerable.sol";

import {ConfigChanged} from "echo/interfaces/PlatformEvents.sol";
import {ITokenMessenger} from "echo/interfaces/ITokenMessenger.sol";
import {Versioned} from "echo/Versioned.sol";

/// @title MultiChainWithdrawer
/// @notice A contract to withdrawn tokens on multiple chains, using CCTP for cross-chain token transfers.
contract MultiChainWithdrawer is AccessControlEnumerable, Versioned(1, 0, 0) {
    using SafeERC20 for IERC20;

    /// @notice The role allowed to perform operational actions but not control money destinations.
    bytes32 public constant PLATFORM_ROLE = keccak256("PLATFORM_ROLE");

    /// @notice The role allowed to perform management actions.
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");

    /// @notice The role allowed to pause the contract
    /// @dev Keeping this deliberately separate from the `PLATFORM_ROLE` since we might want to grant this to some external monitoring in the future
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    /// @notice The role allowed to change the withdrawal addresses
    /// @dev This role is its own admin, and therefore outside the usual role hierarchy.
    bytes32 public constant WITHDRAWAL_MANAGER_ROLE = keccak256("WITHDRAWAL_MANAGER_ROLE");

    error InvalidDomain(uint32 domain);
    error WithdrawalNotEnabled();

    event TokensWithdrawn(bytes32 indexed receiver, uint32 indexed domain, IERC20 indexed token, uint256 amount);

    /// @notice The domain of the chain on which the contract is deployed.
    uint32 public localDomain;

    /// @notice Mapping of CCTP domain to receiver address on the target chain.
    /// @dev Note that we use bytes32 to store the address as some chains have 32 byte addresses (e.g. solana).
    mapping(uint32 => bytes32) public receiverAddressesByDomain;

    /// @notice Flag to enable/disable the deal funding.
    bool public isEnabled;

    /// @notice The token messenger contract.
    ITokenMessenger public tokenMessenger;

    struct Init {
        address admin;
        address manager;
        address platform;
        address withdrawalManager;
        ITokenMessenger tokenMessenger;
        uint32 localDomain;
    }

    constructor(Init memory init) {
        _grantRole(DEFAULT_ADMIN_ROLE, init.admin);
        _grantRole(MANAGER_ROLE, init.manager);
        _grantRole(PAUSER_ROLE, init.manager);
        _grantRole(PLATFORM_ROLE, init.platform);
        _grantRole(WITHDRAWAL_MANAGER_ROLE, init.withdrawalManager);

        // Only withdrawal manager can grant WITHDRAWAL_MANAGER_ROLE
        _setRoleAdmin(WITHDRAWAL_MANAGER_ROLE, WITHDRAWAL_MANAGER_ROLE);

        isEnabled = true;
        localDomain = init.localDomain;
        tokenMessenger = init.tokenMessenger;
    }

    function setWithdrawalAddress(uint32 domain, bytes32 addr) public onlyRole(WITHDRAWAL_MANAGER_ROLE) {
        _setWithdrawalAddress(domain, addr);
    }

    function setWithdrawalAddressEVM(uint32 domain, address addr) public onlyRole(WITHDRAWAL_MANAGER_ROLE) {
        _setWithdrawalAddress(domain, _addressToBytes32(addr));
    }

    /// @notice Withdraws tokens from the contract to a pre-configured address on the destination chain.
    /// @param domain The domain to withdraw to. As defined here: https://developers.circle.com/stablecoins/supported-domains
    /// @param token The token to withdraw. Assumes a Circle compatible token for non-local chains. This is implicitly enforced by Circle needing permissions to burn the token.
    /// @param amount The amount to withdraw.
    function withdraw(uint32 domain, IERC20 token, uint256 amount) public onlyRole(PLATFORM_ROLE) {
        if (!isEnabled) {
            revert WithdrawalNotEnabled();
        }

        bytes32 receiverAddress = receiverAddressesByDomain[domain];
        if (receiverAddress == bytes32(0)) {
            revert InvalidDomain(domain);
        }

        // Just withdraw token directly in this case.
        if (domain == localDomain) {
            _withdrawLocal(token, _bytes32ToAddress(receiverAddress), amount);
            return;
        }

        // Otherwise, we need to withdraw via CCTP.
        token.approve(address(tokenMessenger), amount);
        tokenMessenger.depositForBurn(amount, domain, receiverAddress, address(token));
        emit TokensWithdrawn(receiverAddress, domain, token, amount);
    }

    /// @notice Withdraws tokens from the contract to a given address (assumes contract is deployed on an EVM chain).
    function _withdrawLocal(IERC20 coin, address to, uint256 amount) internal {
        emit TokensWithdrawn(_addressToBytes32(to), localDomain, coin, amount);
        coin.safeTransfer(to, amount);
    }

    /// @notice Sets whether withdrawals are enabled.
    function _setEnabled(bool isEnabled_) internal {
        isEnabled = isEnabled_;
        emit ConfigChanged(this.setEnabled.selector, "setEnabled(bool)", abi.encode(isEnabled_));
    }

    /// @notice Sets the delivery address for a given domain.
    function _setWithdrawalAddress(uint32 domain, bytes32 addr) internal {
        receiverAddressesByDomain[domain] = addr;
        emit ConfigChanged(
            this.setWithdrawalAddress.selector, "setWithdrawalAddress(uint32,bytes32)", abi.encode(domain, addr)
        );
    }

    function _addressToBytes32(address addr) internal pure returns (bytes32) {
        return bytes32(uint256(uint160(addr)));
    }

    function _bytes32ToAddress(bytes32 buf) internal pure returns (address) {
        return address(uint160(uint256(buf)));
    }

    /// @notice Sets whether delivery is enabled.
    function setEnabled(bool isEnabled_) external onlyRole(MANAGER_ROLE) {
        _setEnabled(isEnabled_);
    }

    /// @notice Pauses the deal funding.
    /// @dev Equivalent to `setEnabled(false)`.
    function pause() external onlyRole(PAUSER_ROLE) {
        _setEnabled(false);
    }

    /// @notice Allows the withdrawal manager to recover any tokens sent to the contract.
    /// @dev This is intended as a safeguard and should only be used in emergencies and with utmost care.
    function recoverTokens(IERC20 coin, address to, uint256 amount) external onlyRole(WITHDRAWAL_MANAGER_ROLE) {
        _withdrawLocal(coin, to, amount);
    }
}
