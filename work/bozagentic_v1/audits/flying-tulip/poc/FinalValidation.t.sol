// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;
import "forge-std/Test.sol";

interface IERC20 { function balanceOf(address) external view returns (uint256); }
interface IERC4626 { function maxWithdraw(address) external view returns (uint256); function convertToAssets(uint256) external view returns (uint256); function totalAssets() external view returns (uint256); }
interface IWrapper { function availableToWithdraw() external view returns (uint256); function strategies(uint256) external view returns (address); }
interface IPM { function collateralSupply(address) external view returns (uint256); }

contract FinalValidation is Test {
    address constant PM = 0xbA49d0AC42f4fBA4e24A8677a22218a4dF75ebaA;
    address constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant USDT = 0xdAC17F958D2ee523a2206206994597C13D831ec7;
    address constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant W_USDC = 0x095d8B8D4503D590F647343F7cD880Fa2abbbf59;
    address constant W_USDT = 0x267dF6b637DdCaa7763d94b64eBe09F01b07cB36;
    address constant W_WETH = 0x9d96bac8a4E9A5b51b5b262F316C4e648E44E305;

    function setUp() public { vm.createSelectFork(vm.envString("ETH_RPC_URL")); }

    function test_usdt_liquid_reason() public view {
        address usdtStrat = IWrapper(W_USDT).strategies(0);
        (bool ok, bytes memory ret) = usdtStrat.staticcall(abi.encodeWithSignature("positionToken()"));
        require(ok && ret.length >= 32, "no positionToken");
        address usdtVault = abi.decode(ret, (address));
        uint256 maxW = IERC4626(usdtVault).maxWithdraw(usdtStrat);
        uint256 collSupply = IPM(PM).collateralSupply(USDT);
        assertLe(collSupply, maxW, "USDT within withdrawal limit");
    }

    function test_usdc_shortfall_current() public view {
        assertGt(IPM(PM).collateralSupply(USDC), IWrapper(W_USDC).availableToWithdraw(), "USDC shortfall NOW");
    }

    function test_weth_shortfall_current() public view {
        assertGt(IPM(PM).collateralSupply(WETH), IWrapper(W_WETH).availableToWithdraw(), "wETH shortfall NOW");
    }

    function test_docs_vs_onchain() public view {
        assertNotEq(IWrapper(W_USDC).strategies(0), 0x0987fb9Ae6CDc6E71DeFcf710833ACfc36e3ba7D, "USDC != docs");
        assertNotEq(IWrapper(W_WETH).strategies(0), 0x2e43F825FBA9018D6303E9CF978cAd9Ac54B04AE, "wETH != docs");
    }

    function test_strategies_are_spark() public view {
        (bool hasAToken1,) = IWrapper(W_USDC).strategies(0).staticcall(abi.encodeWithSignature("aToken()"));
        (bool hasPosToken1,) = IWrapper(W_USDC).strategies(0).staticcall(abi.encodeWithSignature("positionToken()"));
        assertFalse(hasAToken1, "USDC not Aave");
        assertTrue(hasPosToken1, "USDC is ERC4626");

        (bool hasAToken2,) = IWrapper(W_WETH).strategies(0).staticcall(abi.encodeWithSignature("aToken()"));
        (bool hasPosToken2,) = IWrapper(W_WETH).strategies(0).staticcall(abi.encodeWithSignature("positionToken()"));
        assertFalse(hasAToken2, "wETH not Aave");
        assertTrue(hasPosToken2, "wETH is ERC4626");
    }

    function test_spark_dsr_mechanism() public view {
        (, bytes memory r1) = IWrapper(W_USDC).strategies(0).staticcall(abi.encodeWithSignature("positionToken()"));
        address usdcVault = abi.decode(r1, (address));
        uint256 liquid = IERC20(USDC).balanceOf(usdcVault);
        uint256 total = IERC4626(usdcVault).totalAssets();
        uint256 maxW = IERC4626(usdcVault).maxWithdraw(IWrapper(W_USDC).strategies(0));
        assertEq(maxW, liquid, "maxWithdraw == liquid");
        assertGt(total, liquid, "rest in DSR");
    }
}
