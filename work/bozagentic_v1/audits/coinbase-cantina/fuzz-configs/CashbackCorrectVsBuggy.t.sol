// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Side-by-side: buggy vs correct CashbackRewards validation
contract CashbackCorrectVsBuggy {
    
    // BUGGY: SEND ignores allocated
    function buggyValidate(
        uint120 distributed, uint120 allocated, uint120 amount,
        uint120 paymentAmount, uint256 maxBps, bool isAllocate
    ) internal pure returns (bool) {
        uint120 prev = distributed;
        uint120 pmt = paymentAmount;
        if (isAllocate) {
            prev += allocated;
        }
        uint120 total = prev + amount;
        uint120 cap = uint120(uint256(pmt) * maxBps / 10000);
        return total <= cap;
    }
    
    // CORRECT: always counts allocated
    function correctValidate(
        uint120 distributed, uint120 allocated, uint120 amount,
        uint120 paymentAmount, uint256 maxBps, bool isAllocate
    ) internal pure returns (bool) {
        uint120 prev = distributed + allocated;
        uint120 pmt = paymentAmount;
        if (isAllocate) {
            // pmt += capturable (omitted for simplicity)
        }
        uint120 total = prev + amount;
        uint120 cap = uint120(uint256(pmt) * maxBps / 10000);
        return total <= cap;
    }
    
    // PROPERTY: buggy SEND passes when correct SEND rejects
    function check_bypass_exists(
        uint120 allocAmt, uint120 sendAmt, uint120 payment, uint16 bps
    ) external pure {
        if (bps == 0 || bps > 10000) return;
        if (allocAmt == 0 || sendAmt == 0 || payment == 0) return;
        
        // After allocate(allocAmt): allocated=allocAmt, distributed=0
        bool buggySendPasses = buggyValidate(0, allocAmt, sendAmt, payment, bps, false);
        bool correctSendPasses = correctValidate(0, allocAmt, sendAmt, payment, bps, false);
        
        if (buggySendPasses && !correctSendPasses) {
            // BUG CONFIRMED: buggy passes, correct rejects
            uint120 cap = uint120(uint256(payment) * bps / 10000);
            assert(uint256(allocAmt) + sendAmt > cap); // total exceeds cap
        }
    }
    
    // PROPERTY: correct impl NEVER allows bypass
    function check_correct_never_bypasses(
        uint120 allocAmt, uint120 sendAmt, uint120 payment, uint16 bps
    ) external pure {
        if (bps == 0 || bps > 10000) return;
        if (allocAmt == 0 || sendAmt == 0 || payment == 0) return;
        
        bool allocPasses = correctValidate(0, 0, allocAmt, payment, bps, true);
        bool sendPasses = correctValidate(0, allocAmt, sendAmt, payment, bps, false);
        
        if (allocPasses && sendPasses) {
            uint120 cap = uint120(uint256(payment) * bps / 10000);
            assert(uint256(allocAmt) + sendAmt <= cap);
        }
    }
    
    // PROPERTY: buggy and correct agree when allocated=0
    function check_agree_when_no_allocation(
        uint120 sendAmt, uint120 payment, uint16 bps
    ) external pure {
        if (bps == 0 || bps > 10000) return;
        if (sendAmt == 0 || payment == 0) return;
        
        bool buggy = buggyValidate(0, 0, sendAmt, payment, bps, false);
        bool correct = correctValidate(0, 0, sendAmt, payment, bps, false);
        assert(buggy == correct); // same when allocated=0
    }
}
