// SPDX-License-Identifier: GPL-3.0-only
pragma solidity ^0.8.23;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {AccessControlEnumerable} from "@openzeppelin/contracts/access/extensions/AccessControlEnumerable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {ConfigChanged} from "echo/interfaces/PlatformEvents.sol";
import {Versioned} from "echo/Versioned.sol";

/// @notice LinearUnlocker is a contract that extends the OZ's VestingWallet contract and implements a linear vesting schedule
/// for a specific locked token. This matches the API for the ECHO_TYPE unlocker lib type.
/// OpenZeppelin's VestingWallet contract found here: https://github.com/OpenZeppelin/openzeppelin-contracts/blob/7b74442c5e87ea51dde41c7f18a209fa5154f1a4/contracts/finance/VestingWallet.sol
contract LinearUnlocker is AccessControlEnumerable, Versioned(1, 0, 0) {
    using SafeERC20 for IERC20;

    error NotBeneficiary();
    error Paused();

    event ERC20Released(address indexed token, uint256 amount);

    /// @notice The role allowed to manage any funds related aspects of the contract
    /// @dev This is intended to be controlled by the IM team.
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");

    /// @notice The role allowed to grant ENG_MANAGER_ROLE
    /// @dev This is intended to be controlled by the ENG multisig.
    bytes32 public constant ENG_ADMIN_ROLE = keccak256("ENG_ADMIN_ROLE");

    /// @notice The role allowed to manage engineering related aspects of the contract, that does not involve any funds.
    /// @dev This is intended to be controlled by the ENG team.
    bytes32 public constant ENG_MANAGER_ROLE = keccak256("ENG_MANAGER_ROLE");

    uint256 private _released;
    mapping(address token => uint256) private _erc20Released;
    uint64 private immutable _start;
    uint64 private immutable _duration;

    address public beneficiary;
    IERC20 public lockedToken;
    bool public paused;

    struct Init {
        IERC20 lockedToken;
        address beneficiary;
        uint64 startTimestamp;
        uint64 durationSeconds;
        address engAdmin;
        address engManager;
        address imAdmin;
        address imManager;
    }

    constructor(Init memory init) payable {
        beneficiary = init.beneficiary;
        lockedToken = init.lockedToken;

        _start = init.startTimestamp;
        _duration = init.durationSeconds;

        _setRoleAdmin(ENG_MANAGER_ROLE, ENG_ADMIN_ROLE);

        _grantRole(DEFAULT_ADMIN_ROLE, init.imAdmin);
        _grantRole(ENG_ADMIN_ROLE, init.engAdmin);
        _grantRole(ENG_MANAGER_ROLE, init.engManager);
        _grantRole(MANAGER_ROLE, init.imManager);
    }

    /// @dev Getter for the start timestamp.
    function start() public view virtual returns (uint256) {
        return _start;
    }

    /// @dev Getter for the vesting duration.
    function duration() public view virtual returns (uint256) {
        return _duration;
    }

    /// @dev Getter for the end timestamp.
    function end() public view virtual returns (uint256) {
        return start() + duration();
    }

    /// @notice Getter for the amount of released `token` tokens.
    function released() public view virtual returns (uint256) {
        return released(address(lockedToken));
    }

    /// @dev Getter for the amount of locked token that is releasable.
    function releasable() public view virtual returns (uint256) {
        return releasable(address(lockedToken));
    }

    /// @dev Release the locked token that has already vested.
    function release() public virtual {
        release(address(lockedToken));
    }

    /// @dev Getter for the amount of releasable `token` tokens. `token` should be the address of an
    /// {IERC20} contract.
    function releasable(address token) public view virtual returns (uint256) {
        return vestedAmount(token, uint64(block.timestamp)) - released(token);
    }

    /// @dev Amount of token already released
    function released(address token) public view virtual returns (uint256) {
        return _erc20Released[token];
    }

    /// @dev Release the tokens that have already vested.
    ///
    /// Emits a {ERC20Released} event.
    function release(address token) public virtual {
        // This is a safeguard to prevent anyone but the beneficiary from releasing tokens. This is useful
        // if the beneficiary was set to the wrong address (i.e. burn address) and the tokens were sent there.
        if (msg.sender != beneficiary) {
            revert NotBeneficiary();
        }

        if (paused) {
            revert Paused();
        }

        uint256 amount = releasable(token);
        _erc20Released[token] += amount;
        emit ERC20Released(token, amount);
        SafeERC20.safeTransfer(IERC20(token), beneficiary, amount);
    }

    /// @dev Calculates the amount of tokens that has already vested. Default implementation is a linear vesting curve.
    function vestedAmount(address token, uint64 timestamp) public view virtual returns (uint256) {
        return _vestingSchedule(IERC20(token).balanceOf(address(this)) + released(token), timestamp);
    }

    /// @dev Virtual implementation of the vesting formula. This returns the amount vested, as a function of time, for
    /// an asset given its total historical allocation.
    function _vestingSchedule(uint256 totalAllocation, uint64 timestamp) internal view virtual returns (uint256) {
        if (timestamp < start()) {
            return 0;
        } else if (timestamp >= end()) {
            return totalAllocation;
        } else {
            return (totalAllocation * (timestamp - start())) / duration();
        }
    }

    /// @dev Allows the IM manager to set the beneficiary address.
    function setBeneficiary(address newBeneficiary) external onlyRole(MANAGER_ROLE) {
        beneficiary = newBeneficiary;
        emit ConfigChanged(this.setBeneficiary.selector, "setBeneficiary(address)", abi.encode(newBeneficiary));
    }

    /// @dev Allows the ENG manager to set the locked token address.
    function setLockedToken(IERC20 newLockedToken) external onlyRole(ENG_MANAGER_ROLE) {
        lockedToken = newLockedToken;
        emit ConfigChanged(this.setLockedToken.selector, "setLockedToken(address)", abi.encode(newLockedToken));
    }

    /// @dev Allows the eng manager to pause the contract.
    function setPaused(bool shouldPause) external onlyRole(ENG_MANAGER_ROLE) {
        paused = shouldPause;
        emit ConfigChanged(this.setPaused.selector, "setPaused(bool)", abi.encode(shouldPause));
    }

    /// @notice Allows the IM manager to recover any tokens sent to the contract.
    /// @dev This is intended as a safeguard and should only be used in emergencies and with utmost care.
    function recoverTokens(IERC20 coin, address to, uint256 amount) external onlyRole(MANAGER_ROLE) {
        coin.safeTransfer(to, amount);
    }
}
