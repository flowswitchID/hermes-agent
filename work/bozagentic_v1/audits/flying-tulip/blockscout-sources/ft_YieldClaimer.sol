// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.30;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {EnumerableSet} from "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";

interface IYieldWrapper {
    function token() external view returns (address);
    function deploy(address strategy, uint256 amount) external;
    function strategies(uint256 index) external view returns (address);
    function setYieldClaimer(address _yieldClaimer) external;
    function setSubYieldClaimer(address _subYieldClaimer) external;
    function confirmStrategyManager() external;
    function confirmTreasury() external;
    function forceWithdrawToWrapper(address strategy, uint256 amount) external;
    function withdrawQueued(address strategy, uint256 amount) external returns (uint256 id);
    function claimQueued(address strategy, uint256 id) external returns (uint256 received);
    function claimYield(address strategy) external returns (uint256 _yield);
    function claimYields() external returns (uint256 _yield);
    function sweepIdleYield() external returns (uint256 amount);
    function execute(
        address strategy,
        address to,
        uint256 value,
        bytes calldata data
    )
        external
        returns (bool success, bytes memory result);
}

contract YieldClaimer is Ownable {
    using EnumerableSet for EnumerableSet.AddressSet;

    EnumerableSet.AddressSet private _wrappers;
    mapping(address keeper => bool) public keepers;
    bool public keepersPaused;

    event WrapperSet(address indexed wrapper);
    event WrapperRemoved(address indexed wrapper);
    event ClaimFailed(address indexed wrapper);
    error YieldClaimerZeroAddress();
    error YieldClaimerWrapperNotWhitelisted();
    error YieldClaimerWrapperAlreadyWhitelisted();
    error YieldClaimerNotKeeper();
    error YieldClaimerKeepersPaused();

    constructor(address initialOwner) Ownable(initialOwner) {}

    modifier onlyKeeper() {
        if (msg.sender == owner()) {
            _;
            return;
        }

        if (keepersPaused) {
            revert YieldClaimerKeepersPaused();
        }
        if (!keepers[msg.sender]) {
            revert YieldClaimerNotKeeper();
        }
        _;
    }

    function addWrapper(address wrapper) external onlyOwner {
        if (wrapper == address(0)) {
            revert YieldClaimerZeroAddress();
        }

        if (!_wrappers.add(wrapper)) {
            revert YieldClaimerWrapperAlreadyWhitelisted();
        }
        emit WrapperSet(wrapper);
    }

    function removeWrapper(address wrapper) external onlyOwner {
        if (!_wrappers.remove(wrapper)) {
            revert YieldClaimerWrapperNotWhitelisted();
        }
        emit WrapperRemoved(wrapper);
    }

    function setKeeper(address keeper, bool allowed) external onlyOwner {
        if (keeper == address(0)) {
            revert YieldClaimerZeroAddress();
        }
        keepers[keeper] = allowed;
    }

    function setKeeperPause(bool paused) external onlyOwner {
        keepersPaused = paused;
    }

    function setYieldClaimer(address wrapper, address newYieldClaimer) external onlyOwner {
        _requireWhitelisted(wrapper);
        IYieldWrapper(wrapper).setYieldClaimer(newYieldClaimer);
    }

    function setSubYieldClaimer(address wrapper, address newSubYieldClaimer) external onlyOwner {
        _requireWhitelisted(wrapper);
        IYieldWrapper(wrapper).setSubYieldClaimer(newSubYieldClaimer);
    }

    function confirmStrategyManager(address wrapper) external onlyOwner {
        _requireWhitelisted(wrapper);
        IYieldWrapper(wrapper).confirmStrategyManager();
    }

    function confirmTreasury(address wrapper) external onlyOwner {
        _requireWhitelisted(wrapper);
        IYieldWrapper(wrapper).confirmTreasury();
    }

    function deploy(address wrapper, address strategy, uint256 amount) external onlyOwner {
        _requireWhitelisted(wrapper);
        IYieldWrapper(wrapper).deploy(strategy, amount);
    }

    // Security hardening: execute is owner-only (keepers cannot call), even though wrapper allows yield claimers.
    function execute(
        address wrapper,
        address strategy,
        address to,
        uint256 value,
        bytes calldata data
    )
        external
        onlyOwner
        returns (bool success, bytes memory result)
    {
        _requireWhitelisted(wrapper);
        (success, result) = IYieldWrapper(wrapper).execute(strategy, to, value, data);
    }

    // Security hardening: forceWithdrawToWrapper is owner-only (keepers cannot call).
    function forceWithdrawToWrapper(
        address wrapper,
        address strategy,
        uint256 amount
    )
        external
        onlyOwner
    {
        _requireWhitelisted(wrapper);
        IYieldWrapper(wrapper).forceWithdrawToWrapper(strategy, amount);
    }

    // Security hardening: withdrawQueued is owner-only (keepers cannot call).
    function withdrawQueued(
        address wrapper,
        address strategy,
        uint256 amount
    )
        external
        onlyOwner
        returns (uint256 id)
    {
        _requireWhitelisted(wrapper);
        id = IYieldWrapper(wrapper).withdrawQueued(strategy, amount);
    }

    // Security hardening: claimQueued is owner-only (keepers cannot call).
    function claimQueued(
        address wrapper,
        address strategy,
        uint256 id
    )
        external
        onlyOwner
        returns (uint256 received)
    {
        _requireWhitelisted(wrapper);
        received = IYieldWrapper(wrapper).claimQueued(strategy, id);
    }

    // Helper for keeper callers (not part of wrapper): deploys idle wrapper balance
    // to the first strategy in the wrapper queue (strategies(0)) for all whitelisted wrappers.
    function deployAll() external onlyKeeper {
        uint256 length = _wrappers.length();
        for (uint256 i = 0; i < length; ++i) {
            _deployWrapper(_wrappers.at(i));
        }
    }

    // Helper for keeper callers (not part of wrapper): same as deployAll() but only
    // for the provided wrapper list; still deploys to strategies(0) for each wrapper.
    function deployAll(address[] calldata wrapperList) external onlyKeeper {
        uint256 length = wrapperList.length;
        for (uint256 i = 0; i < length; ++i) {
            _requireWhitelisted(wrapperList[i]);
            _deployWrapper(wrapperList[i]);
        }
    }

    function claimYield(
        address wrapper,
        address strategy
    )
        external
        onlyKeeper
        returns (uint256 _yield)
    {
        _requireWhitelisted(wrapper);
        _yield = IYieldWrapper(wrapper).claimYield(strategy);
    }

    function claimYields(address wrapper) external onlyKeeper returns (uint256 _yield) {
        _requireWhitelisted(wrapper);
        _yield = IYieldWrapper(wrapper).claimYields();
    }

    function claimAll() external onlyKeeper {
        uint256 length = _wrappers.length();
        for (uint256 i = 0; i < length; ++i) {
            _claimWrapper(_wrappers.at(i));
        }
    }

    function claimAll(address[] calldata wrapperList) external onlyKeeper {
        uint256 length = wrapperList.length;
        for (uint256 i = 0; i < length; ++i) {
            _requireWhitelisted(wrapperList[i]);
            _claimWrapper(wrapperList[i]);
        }
    }

    function sweepIdleYield(address wrapper) external onlyKeeper returns (uint256 amount) {
        _requireWhitelisted(wrapper);
        amount = IYieldWrapper(wrapper).sweepIdleYield();
    }

    function wrappers() external view returns (address[] memory) {
        return _wrappers.values();
    }

    function _deployWrapper(address wrapper) internal {
        address strategy = IYieldWrapper(wrapper).strategies(0);
        address token = IYieldWrapper(wrapper).token();
        uint256 amount = IERC20(token).balanceOf(wrapper);
        if (amount == 0) return;

        IYieldWrapper(wrapper).deploy(strategy, amount);
    }

    function _claimWrapper(address wrapper) internal {
        // Best-effort batch: swallow per-wrapper failures to avoid blocking others.
        try IYieldWrapper(wrapper).claimYields() returns (uint256) {}
        catch {
            emit ClaimFailed(wrapper);
        }
    }

    function _requireWhitelisted(address wrapper) internal view {
        if (!_wrappers.contains(wrapper)) {
            revert YieldClaimerWrapperNotWhitelisted();
        }
    }
}
