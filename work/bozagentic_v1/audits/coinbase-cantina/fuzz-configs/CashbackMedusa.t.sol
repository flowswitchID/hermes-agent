// SPDX-License-Identifier: MIT
pragma solidity ^0.8.29;

import {CashbackRewards} from "../../src/hooks/CashbackRewards.sol";
import {Flywheel} from "../../src/Flywheel.sol";
import {AuthCaptureEscrow} from "commerce-payments/AuthCaptureEscrow.sol";

contract MockEscrowMedusa {
    bytes32 public hash = keccak256("medusa-test");
    function getHash(AuthCaptureEscrow.PaymentInfo calldata) external view returns (bytes32) { return hash; }
    function paymentState(bytes32) external pure returns (bool, uint120, uint120) {
        return (true, 0, 100_000);
    }
}

contract CashbackMedusa {
    CashbackRewards public cb;
    MockEscrowMedusa public escrow;
    Flywheel public fw;
    address campaign;
    
    constructor() {
        escrow = new MockEscrowMedusa();
        fw = new Flywheel();
        cb = new CashbackRewards(address(fw), address(escrow));
        bytes memory hookData = abi.encode(address(this), address(this), "test://", uint16(5000));
        campaign = fw.createCampaign(address(cb), 0, hookData);
    }
    
    function allocateAndSend(uint128 allocAmt, uint128 sendAmt) external {
        if (allocAmt == 0) allocAmt = 1;
        if (sendAmt == 0) sendAmt = 1;
        if (allocAmt > 50_000) allocAmt = 50_000;
        if (sendAmt > 50_000) sendAmt = 50_000;
        
        bytes32 paymentHash = keccak256("medusa-test");
        (uint120 allocated, uint120 distributed) = cb.rewards(campaign, paymentHash);
        uint256 total = uint256(allocated) + uint256(distributed);
        assert(total <= 50_000);
    }
    
    function echidna_cap() external view returns (bool) {
        bytes32 paymentHash = keccak256("medusa-test");
        (uint120 allocated, uint120 distributed) = cb.rewards(campaign, paymentHash);
        return uint256(allocated) + uint256(distributed) <= 50_000;
    }
}
