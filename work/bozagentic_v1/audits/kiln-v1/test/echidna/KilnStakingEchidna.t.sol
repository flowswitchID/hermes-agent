// SPDX-License-Identifier: MIT
pragma solidity >=0.8.10;

import "forge-std/Test.sol";
import "../../src/contracts/StakingContract.sol";
import "../../src/contracts/ConsensusLayerFeeDispatcher.sol";
import "../../src/contracts/ExecutionLayerFeeDispatcher.sol";
import "../../src/contracts/FeeRecipient.sol";

contract MockDeposit {
    function deposit(bytes calldata, bytes calldata, bytes calldata, bytes32) external payable {}
}

contract KilnStakingEchidna is Test {
    StakingContract staking;
    ConsensusLayerFeeDispatcher clDispatcher;
    ExecutionLayerFeeDispatcher elDispatcher;
    FeeRecipient feeRecipientImpl;
    MockDeposit depositContract;

    address admin = address(0xAD);
    address treasury = address(0x77);
    address operator = address(0x09);
    address operatorFee = address(0x0F);

    constructor() {
        depositContract = new MockDeposit();
        clDispatcher = new ConsensusLayerFeeDispatcher(0);
        elDispatcher = new ExecutionLayerFeeDispatcher(0);
        feeRecipientImpl = new FeeRecipient();
        staking = new StakingContract();

        staking.initialize_1(
            admin, treasury, address(depositContract),
            address(elDispatcher), address(clDispatcher),
            address(feeRecipientImpl),
            1000, 5000, 1000, 10000
        );
        clDispatcher.initCLD(address(staking));
        elDispatcher.initELD(address(staking));

        vm.prank(admin);
        staking.addOperator(operator, operatorFee);

        bytes memory pubKeys = new bytes(480);
        bytes memory sigs = new bytes(960);
        for (uint i = 0; i < 480; i++) pubKeys[i] = bytes1(uint8(i % 256));
        for (uint i = 0; i < 960; i++) sigs[i] = bytes1(uint8(i % 256));

        vm.prank(operator);
        staking.addValidators(0, 10, pubKeys, sigs);

        vm.prank(admin);
        staking.setOperatorLimit(0, 10, block.number);
    }

    function echidna_validatorAccounting() public view returns (bool) {
        (,,,, uint256 funded, uint256 available,) = staking.getOperator(0);
        return funded + available <= 10;
    }

    function echidna_noStuckFunds() public view returns (bool) {
        return address(staking).balance == 0;
    }

    function deposit32() public {
        staking.deposit{value: 32 ether}();
    }

    function deposit64() public {
        if (staking.getAvailableValidatorCount() >= 2) {
            staking.deposit{value: 64 ether}();
        }
    }

    receive() external payable {}
}
