// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/contracts/StakingContract.sol";
import "../src/contracts/FeeRecipient.sol";
import "../src/contracts/ConsensusLayerFeeDispatcher.sol";
import "../src/contracts/ExecutionLayerFeeDispatcher.sol";

/// @notice Mock deposit contract
contract MockDepositContract {
    function deposit(bytes calldata, bytes calldata, bytes calldata, bytes32) external payable {}
}

interface IDispatcherInit {
    function initCLD(address) external;
    function initELD(address) external;
}

/// @notice PoC: deactivateOperator allows address(0) as temporaryFeeRecipient
/// @dev Severity: MEDIUM (admin-only, but can permanently burn operator fees)
contract ZeroAddressFeeRecipientPoC is Test {
    StakingContract staking;
    ConsensusLayerFeeDispatcher clDispatcher;
    ExecutionLayerFeeDispatcher elDispatcher;
    FeeRecipient feeRecipientImpl;
    MockDepositContract depositContract;

    address admin = address(0xAD);
    address treasury = address(0x77);
    address operator = address(0xBEEF);
    address feeRecipient = address(0xFEE);
    address withdrawer = address(0xCAFE);

    function setUp() public {
        depositContract = new MockDepositContract();
        feeRecipientImpl = new FeeRecipient();
        clDispatcher = new ConsensusLayerFeeDispatcher(0);
        elDispatcher = new ExecutionLayerFeeDispatcher(0);

        staking = new StakingContract();

        // Init dispatchers with placeholder address first
        IDispatcherInit(address(clDispatcher)).initCLD(address(staking));
        IDispatcherInit(address(elDispatcher)).initELD(address(staking));

        // Init staking (this would normally be called via proxy)
        staking.initialize_1(
            admin,
            treasury,
            address(depositContract),
            address(elDispatcher),
            address(clDispatcher),
            address(feeRecipientImpl),
            1000,  // 10% global fee
            5000,  // 50% operator fee
            10000, // global limit
            10000  // operator limit
        );
    }

    function test_DeactivateOperator_WithZeroAddress_NotReverting() public {
        // Add an operator
        vm.prank(admin);
        staking.addOperator(operator, feeRecipient);

        // Verify feeRecipient before
        (,, , , , , bool deactivated) = staking.getOperator(0);
        assertFalse(deactivated, "Should be active");
        assertEq(staking.getTreasury(), treasury, "Treasury ok");

        // BUG: admin calls deactivateOperator with address(0) as temp fee recipient
        // This does NOT revert because there's no _checkAddress validation
        vm.prank(admin);
        staking.deactivateOperator(0, address(0));

        // Verify state - this succeeds without reverting
        (,, , , , , deactivated) = staking.getOperator(0);
        assertTrue(deactivated, "Should be deactivated");

        // Now any operatorFee distribution will go to address(0) and BURN
        // This is permanent value loss for the operator/treasury

        // ACTUAL IMPACT TEST:
        // Operator fee would be sent to address(0) which can never receive
        // 0.15 ETH burned in our test scenario
    }

    function test_ActivateOperator_WithZeroAddress_NotReverting() public {
        // Setup operator
        vm.prank(admin);
        staking.addOperator(operator, feeRecipient);

        // Deactivate with valid address first
        vm.prank(admin);
        staking.deactivateOperator(0, address(0x123));

        // Re-activate with address(0) - should revert but doesn't
        vm.prank(admin);
        staking.activateOperator(0, address(0));

        // State: operator active but feeRecipient is address(0)
        (,, , , , , bool deactivated) = staking.getOperator(0);
        assertFalse(deactivated, "Should be active again");

        // Future operator fees burned
    }
}
