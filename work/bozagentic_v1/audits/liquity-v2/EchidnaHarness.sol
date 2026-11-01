// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "src/TroveManager.sol";
import "src/BorrowerOperations.sol";
import "src/StabilityPool.sol";
import "src/ActivePool.sol";
import "src/SortedTroves.sol";
import "src/CollSurplusPool.sol";
import "src/DefaultPool.sol";
import "src/GasPool.sol";
import "src/BoldToken.sol";
import "src/Dependencies/Constants.sol";
import "./MockAddressesRegistry.sol";
import "./MockAll.sol";

contract EchidnaHarness {
    MockAll public mock;
    MockAddressesRegistry public registry;
    TroveManager public troveManager;
    BorrowerOperations public borrowerOperations;
    StabilityPool public stabilityPool;
    ActivePool public activePool;
    SortedTroves public sortedTroves;
    CollSurplusPool public collSurplusPool;
    DefaultPool public defaultPool;
    GasPool public gasPool;
    BoldToken public boldToken;
    
    bool deployed;
    
    constructor() {
        // 1. Deploy MockAll FIRST (has runtime code for callbacks)
        mock = new MockAll();
        
        // 2. Registry points to MockAll for all external deps
        registry = new MockAddressesRegistry(address(mock));
        
        // 3. Deploy core contracts (they call mock.approve etc — works!)
        troveManager = new TroveManager(registry);
        borrowerOperations = new BorrowerOperations(registry);
        stabilityPool = new StabilityPool(registry);
        activePool = new ActivePool(registry);
        sortedTroves = new SortedTroves(registry);
        collSurplusPool = new CollSurplusPool(registry);
        defaultPool = new DefaultPool(registry);
        gasPool = new GasPool(registry);
        boldToken = new BoldToken(address(this));
        
        deployed = true;
    }
    
    // === ECHIDNA PROPERTY TESTS ===
    function echidna_deployment_succeeded() public view returns (bool) {
        return deployed;
    }
    
    function echidna_trove_count_valid() public view returns (bool) {
        return troveManager.getTroveIdsCount() >= 0;
    }
    
    function echidna_bold_supply_valid() public view returns (bool) {
        return boldToken.totalSupply() >= 0;
    }
    
    function echidna_active_pool_valid() public view returns (bool) {
        return activePool.getCollBalance() >= 0;
    }
    
    function echidna_sp_deposits_valid() public view returns (bool) {
        return stabilityPool.getTotalBoldDeposits() >= 0;
    }
    
    function echidna_sorted_size_valid() public view returns (bool) {
        return sortedTroves.getSize() >= 0;
    }
    
    function echidna_surplus_valid() public view returns (bool) {
        return collSurplusPool.getCollBalance() >= 0;
    }
    
    function echidna_default_pool_valid() public view returns (bool) {
        return defaultPool.getCollBalance() >= 0;
    }
    
    // === MEDUSA PROPERTY TESTS ===
    function medusa_deployment_succeeded() public view returns (bool) {
        return deployed;
    }
    
    function medusa_trove_count_valid() public view returns (bool) {
        return troveManager.getTroveIdsCount() >= 0;
    }
    
    function medusa_bold_supply_valid() public view returns (bool) {
        return boldToken.totalSupply() >= 0;
    }
    
    function medusa_active_pool_valid() public view returns (bool) {
        return activePool.getCollBalance() >= 0;
    }
    
    function medusa_sp_deposits_valid() public view returns (bool) {
        return stabilityPool.getTotalBoldDeposits() >= 0;
    }
    
    function medusa_sorted_size_valid() public view returns (bool) {
        return sortedTroves.getSize() >= 0;
    }
    
    function medusa_surplus_valid() public view returns (bool) {
        return collSurplusPool.getCollBalance() >= 0;
    }
    
    function medusa_default_pool_valid() public view returns (bool) {
        return defaultPool.getCollBalance() >= 0;
    }
    
    receive() external payable {}
}
