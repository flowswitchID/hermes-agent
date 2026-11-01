// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;
import "forge-std/Test.sol";

interface IERC20 { function balanceOf(address) external view returns (uint256); }
interface IERC4626 { function maxWithdraw(address) external view returns (uint256); function convertToAssets(uint256) external view returns (uint256); function totalAssets() external view returns (uint256); }
interface IWrapper { function availableToWithdraw() external view returns (uint256); function canWithdraw(uint256) external view returns (bool); function strategies(uint256) external view returns (address); }
interface IPM { function collateralSupply(address) external view returns (uint256); }

contract SparkWithdrawalCapPoC is Test {
    address constant PM     = 0xbA49d0AC42f4fBA4e24A8677a22218a4dF75ebaA;
    address constant W_USDC = 0x095d8B8D4503D590F647343F7cD880Fa2abbbf59;
    address constant W_WETH = 0x9d96bac8a4E9A5b51b5b262F316C4e648E44E305;
    address constant USDC   = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant WETH   = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant spUSDC = 0x28B3a8fb53B741A8Fd78c0fb9A6B2393d896a43d;
    address constant spETH  = 0xfE6eb3b609a7C8352A241f7F3A21CEA4e9209B8f;
    address constant STRAT_USDC = 0xCFb9D82C426335C458ED78625B29B013c632FF2C;
    address constant STRAT_WETH = 0x3f537EF4313297b53BB827C02f3CC381Ad080AEb;
    address constant DOCS_STRAT_USDC = 0x0987fb9Ae6CDc6E71DeFcf710833ACfc36e3ba7D;
    address constant DOCS_STRAT_WETH = 0x2e43F825FBA9018D6303E9CF978cAd9Ac54B04AE;

    function setUp() public {
        vm.createSelectFork(vm.envString("ETH_RPC_URL"));
    }

    // PROOF 1: Strategies changed from Aave (docs) to Spark (actual)
    function test_proof1_strategies_changed() public view {
        assertNotEq(IWrapper(W_USDC).strategies(0), DOCS_STRAT_USDC, "USDC strat != docs");
        assertNotEq(IWrapper(W_WETH).strategies(0), DOCS_STRAT_WETH, "wETH strat != docs");
        assertEq(IWrapper(W_USDC).strategies(0), STRAT_USDC, "USDC is Spark");
        assertEq(IWrapper(W_WETH).strategies(0), STRAT_WETH, "wETH is Spark");
        (bool hasAToken,) = STRAT_USDC.staticcall(abi.encodeWithSignature("aToken()"));
        assertFalse(hasAToken, "Not AaveStrategy");
    }

    // PROOF 2: USDC Spark vault maxWithdraw < full position
    function test_proof2_usdc_cap() public view {
        uint256 full = IERC4626(spUSDC).convertToAssets(IERC20(spUSDC).balanceOf(STRAT_USDC));
        uint256 maxW = IERC4626(spUSDC).maxWithdraw(STRAT_USDC);
        assertLt(maxW, full, "USDC maxWithdraw < full position");
        assertEq(maxW, IERC20(USDC).balanceOf(spUSDC), "maxWithdraw == liquid");
    }

    // PROOF 3: wETH Spark vault maxWithdraw < full position
    function test_proof3_weth_cap() public view {
        uint256 full = IERC4626(spETH).convertToAssets(IERC20(spETH).balanceOf(STRAT_WETH));
        uint256 maxW = IERC4626(spETH).maxWithdraw(STRAT_WETH);
        assertLt(maxW, full, "wETH maxWithdraw < full position");
    }

    // PROOF 4: USDC bank run — collateralSupply > availableToWithdraw
    function test_proof4_usdc_bank_run() public view {
        uint256 c = IPM(PM).collateralSupply(USDC);
        uint256 a = IWrapper(W_USDC).availableToWithdraw();
        assertGt(c, a, "USDC: not all PUTs can divest");
    }

    // PROOF 5: wETH bank run — collateralSupply > availableToWithdraw
    function test_proof5_weth_bank_run() public view {
        uint256 c = IPM(PM).collateralSupply(WETH);
        uint256 a = IWrapper(W_WETH).availableToWithdraw();
        assertGt(c, a, "wETH: not all PUTs can divest");
    }

    // PROOF 6: canWithdraw returns false for full collateral
    function test_proof6_canWithdraw_false() public view {
        assertFalse(IWrapper(W_USDC).canWithdraw(IPM(PM).collateralSupply(USDC)), "canWithdraw(full)=false");
    }

    // PROOF 7: Aave strategies are fully liquid (contrast)
    function test_proof7_aave_liquid() public view {
        address[4] memory t = [
            0xdAC17F958D2ee523a2206206994597C13D831ec7,
            0xdC035D45d973E3EC169d2276DDab16f1e407384F,
            0xC139190F447e929f090Edeb554D95AbB8b18aC1C,
            0x4c9EDD5852cd905f086C759E8383e09bff1E68B3
        ];
        address[4] memory w = [
            0x267dF6b637DdCaa7763d94b64eBe09F01b07cB36,
            0xA143a9C486a1A4aaf54FAEFF7252CECe2d337573,
            0xE5270E0458f58b83dB3d90Aa6A616173c98C97b6,
            0xe6880Fc961b1235c46552E391358A270281b5625
        ];
        for (uint i = 0; i < 4; i++) {
            uint256 cs = IPM(PM).collateralSupply(t[i]);
            if (cs == 0) continue;
            assertGe(IWrapper(w[i]).availableToWithdraw(), cs, "Aave liquid");
        }
    }

    // PROOF 8: Root cause — Spark deploys to DSR
    function test_proof8_dsr_root_cause() public view {
        uint256 liquid = IERC20(USDC).balanceOf(spUSDC);
        uint256 total  = IERC4626(spUSDC).totalAssets();
        assertEq(IERC4626(spUSDC).maxWithdraw(STRAT_USDC), liquid, "cap == liquid");
        assertGt(total, liquid, "rest in DSR");
    }
}
