// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.30;

import {
    IERC20Metadata,
    IERC20
} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuardTransient} from "@openzeppelin/contracts/utils/ReentrancyGuardTransient.sol";
import {IERC4626} from "@openzeppelin/contracts/interfaces/IERC4626.sol";
import {IStrategy} from "../interfaces/IStrategy.sol";

/// @notice Generalized Spark Savings strategy for any ERC-4626 Spark Vault (spUSDC, spUSDT, etc.).
///         Deposits underlying into the vault, tracks principal 1:1, and skims yield as vault
///         shares to the treasury.
contract SparkSavingsStrategy is IStrategy, ERC20, ReentrancyGuardTransient {
    using SafeERC20 for IERC20;

    address public immutable token;
    IERC4626 public immutable vault;

    address public ftYieldWrapper;

    modifier onlyftYieldWrapper() {
        if (msg.sender != ftYieldWrapper) revert StrategyNotYieldWrapper();
        _;
    }

    constructor(
        address _ftYieldWrapper,
        address _token,
        address _vault
    )
        ERC20(
            string.concat("Flying Tulip Spark ", IERC20Metadata(_token).name()),
            string.concat("ftSpark", IERC20Metadata(_token).symbol())
        )
    {
        if (_ftYieldWrapper == address(0)) revert StrategyZeroAddress();

        ftYieldWrapper = _ftYieldWrapper;
        token = _token;
        vault = IERC4626(_vault);

        if (vault.asset() != _token) revert StrategyAssetMismatch();
        if (IERC20Metadata(_token).decimals() != vault.decimals()) {
            revert StrategyDecimalsMismatch();
        }

        emit Transfer(address(0x0), address(this), 0);
    }

    // --- Admin ---

    function setftYieldWrapper(address _ftYieldWrapper) external onlyftYieldWrapper {
        if (_ftYieldWrapper == address(0)) revert StrategyZeroAddress();
        ftYieldWrapper = _ftYieldWrapper;
        emit UpdateftYieldWrapper(_ftYieldWrapper);
    }

    // --- Accounting views ---

    function capital() external view returns (uint256) {
        return totalSupply();
    }

    function valueOfCapital() public view returns (uint256) {
        uint256 shares = vault.balanceOf(address(this));
        return vault.convertToAssets(shares);
    }

    function yield() public view returns (uint256) {
        uint256 v = valueOfCapital();
        uint256 t = totalSupply();
        return (v > t) ? (v - t) : 0;
    }

    function availableToWithdraw() public view returns (uint256) {
        uint256 vaultLimit = vault.maxWithdraw(address(this));
        uint256 _capital = totalSupply();
        if (vaultLimit > _capital) vaultLimit = _capital;
        uint256 ownedAssets = valueOfCapital();
        if (vaultLimit > ownedAssets) vaultLimit = ownedAssets;
        return vaultLimit;
    }

    function canWithdraw(uint256 amount) external view returns (bool) {
        return availableToWithdraw() >= amount;
    }

    function maxAbleToWithdraw(uint256 amount) external view returns (uint256) {
        uint256 a = availableToWithdraw();
        return (a > amount) ? amount : a;
    }

    // --- Core actions ---

    function deposit(uint256 amount) external nonReentrant onlyftYieldWrapper {
        if (amount == 0) revert StrategyAmountZero();

        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        IERC20(token).forceApprove(address(vault), amount);
        vault.deposit(amount, address(this));

        _mint(msg.sender, amount);
        emit Deposit(msg.sender, amount);
    }

    function withdraw(uint256 amount)
        external
        nonReentrant
        onlyftYieldWrapper
        returns (uint256 received)
    {
        uint256 avail = availableToWithdraw();
        if (amount == 0 || amount > avail) {
            revert StrategyInsufficientLiquidity();
        }

        _burn(msg.sender, amount);
        vault.withdraw(amount, msg.sender, address(this));

        emit Withdraw(msg.sender, amount);
        return amount;
    }

    /// @dev Appreciation-style exit: ERC-4626 vault shares appreciate over time, so
    ///      received (vault shares) < amount (underlying).
    /// @param amount Underlying-denominated principal to exit (e.g. 100 USDC).
    /// @return shares Number of vault shares transferred (fewer than `amount` because each
    ///         share is worth > 1 underlying unit).
    function withdrawUnderlying(uint256 amount)
        external
        nonReentrant
        onlyftYieldWrapper
        returns (uint256 shares)
    {
        if (amount == 0) revert StrategyAmountZero();

        shares = vault.convertToShares(amount);
        if (shares == 0) revert StrategyInsufficientLiquidity();

        uint256 ourShares = vault.balanceOf(address(this));
        if (shares > ourShares) revert StrategyInsufficientLiquidity();

        _burn(msg.sender, amount);
        IERC20(address(vault)).safeTransfer(msg.sender, shares);
        emit WithdrawUnderlying(msg.sender, amount);
    }

    // --- Yield ---

    function claimYield(address treasury)
        external
        nonReentrant
        onlyftYieldWrapper
        returns (uint256 assetsYield)
    {
        assetsYield = yield();
        if (assetsYield == 0) return 0;

        // Round down to avoid transferring more shares than the yield is worth,
        // which would dip below principal. At most 1 unit of yield stays unclaimed.
        uint256 sharesNeeded = vault.convertToShares(assetsYield);

        IERC20(address(vault)).safeTransfer(treasury, sharesNeeded);

        if (valueOfCapital() < totalSupply()) {
            revert StrategyCapitalMustNotChange();
        }

        emit YieldClaimed(msg.sender, treasury, address(vault), sharesNeeded);
        return assetsYield;
    }

    // --- Utility / Guardrail ---

    function execute(
        address to,
        uint256 value,
        bytes calldata data
    )
        external
        nonReentrant
        onlyftYieldWrapper
        returns (bool success, bytes memory result)
    {
        if (to == address(vault) || to == address(this)) {
            revert StrategyCantInteractWithCoreAssets();
        }
        (success, result) = to.call{value: value}(data);
        if (valueOfCapital() < totalSupply()) {
            revert StrategyCapitalMustNotChange();
        }
    }

    function decimals() public view override(ERC20, IERC20Metadata) returns (uint8) {
        return IERC20Metadata(token).decimals();
    }

    function positionToken() external view returns (address) {
        return address(vault);
    }
}
