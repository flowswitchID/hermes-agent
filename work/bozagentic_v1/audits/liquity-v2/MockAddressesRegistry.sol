// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "src/Interfaces/IAddressesRegistry.sol";
import "src/Dependencies/Constants.sol";

// Mock registry that returns a configurable address for all getters
contract MockAddressesRegistry is IAddressesRegistry {
    address public target;
    
    constructor(address _target) {
        target = _target;
    }
    
    function collToken() external view returns (IERC20Metadata) { return IERC20Metadata(target); }
    function borrowerOperations() external view returns (IBorrowerOperations) { return IBorrowerOperations(target); }
    function troveManager() external view returns (ITroveManager) { return ITroveManager(target); }
    function troveNFT() external view returns (ITroveNFT) { return ITroveNFT(target); }
    function metadataNFT() external view returns (IMetadataNFT) { return IMetadataNFT(target); }
    function stabilityPool() external view returns (IStabilityPool) { return IStabilityPool(target); }
    function priceFeed() external view returns (IPriceFeed) { return IPriceFeed(target); }
    function activePool() external view returns (IActivePool) { return IActivePool(target); }
    function defaultPool() external view returns (IDefaultPool) { return IDefaultPool(target); }
    function gasPoolAddress() external view returns (address) { return target; }
    function collSurplusPool() external view returns (ICollSurplusPool) { return ICollSurplusPool(target); }
    function sortedTroves() external view returns (ISortedTroves) { return ISortedTroves(target); }
    function interestRouter() external view returns (IInterestRouter) { return IInterestRouter(target); }
    function hintHelpers() external view returns (IHintHelpers) { return IHintHelpers(target); }
    function multiTroveGetter() external view returns (IMultiTroveGetter) { return IMultiTroveGetter(target); }
    function collateralRegistry() external view returns (ICollateralRegistry) { return ICollateralRegistry(target); }
    function boldToken() external view returns (IBoldToken) { return IBoldToken(target); }
    function WETH() external view returns (IWETH) { return IWETH(target); }
    
    function CCR() external pure returns (uint256) { return CCR_WETH; }
    function SCR() external pure returns (uint256) { return SCR_WETH; }
    function MCR() external pure returns (uint256) { return MCR_WETH; }
    function BCR() external pure returns (uint256) { return BCR_ALL; }
    function LIQUIDATION_PENALTY_SP() external pure returns (uint256) { return LIQUIDATION_PENALTY_SP_WETH; }
    function LIQUIDATION_PENALTY_REDISTRIBUTION() external pure returns (uint256) { return LIQUIDATION_PENALTY_REDISTRIBUTION_WETH; }
    
    function setAddresses(AddressVars memory) external {}
}
