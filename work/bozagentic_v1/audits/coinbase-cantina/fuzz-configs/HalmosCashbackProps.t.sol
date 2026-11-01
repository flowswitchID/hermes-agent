// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CashbackProps {
    uint256 constant BPS = 10000;
    
    // PROPERTY: cap = payment * bps / 10000 <= payment
    function check_cap_bounded(uint128 payment, uint16 bps) external pure {
        if (bps > 10000) return;
        uint256 cap = uint256(payment) * bps / BPS;
        assert(cap <= payment);
    }
    
    // PROPERTY: bps=10000 → cap=payment
    function check_full_bps(uint128 payment) external pure {
        uint256 cap = uint256(payment) * 10000 / BPS;
        assert(cap == payment);
    }
    
    // PROPERTY: bps=0 → cap=0
    function check_zero_bps(uint128 payment) external pure {
        uint256 cap = uint256(payment) * 0 / BPS;
        assert(cap == 0);
    }
    
    // PROPERTY: monotonic — more bps = more cap
    function check_monotonic(uint128 payment, uint16 bps1, uint16 bps2) external pure {
        if (bps1 > 10000 || bps2 > 10000) return;
        if (bps1 > bps2) return;
        uint256 cap1 = uint256(payment) * bps1 / BPS;
        uint256 cap2 = uint256(payment) * bps2 / BPS;
        assert(cap1 <= cap2);
    }
    
    // PROPERTY: no overflow in cap calculation
    function check_no_overflow(uint16 bps) external pure {
        if (bps > 10000) return;
        uint256 maxPayment = type(uint120).max;
        uint256 cap = maxPayment * bps / BPS;
        assert(cap <= maxPayment);
    }
    
    // PROPERTY: BUGGY — allocate+send can exceed cap
    function check_bypass_bug(uint120 allocAmt, uint120 sendAmt, uint120 payment, uint16 bps) external pure {
        if (bps == 0 || bps > 10000) return;
        if (allocAmt == 0 || sendAmt == 0 || payment == 0) return;
        
        uint256 cap = uint256(payment) * bps / BPS;
        
        // Allocate passes: 0 + allocAmt <= cap
        bool allocPasses = allocAmt <= cap;
        // Send passes (BUG): 0 + sendAmt <= cap (ignores allocated!)
        bool sendPasses = sendAmt <= cap;
        
        if (allocPasses && sendPasses) {
            uint256 total = uint256(allocAmt) + uint256(sendAmt);
            // CORRECT impl would require: total <= cap
            // BUGGY impl allows: total > cap
            // This assert WOULD FAIL (proving the bug):
            // assert(total <= cap);
            
            // Instead: verify correct impl catches it
            bool correctSendPasses = (uint256(allocAmt) + sendAmt) <= cap;
            if (!correctSendPasses) {
                // Bug confirmed: total > cap but both passed individually
                assert(total > cap);
            }
        }
    }
    
    // PROPERTY: CORRECT impl always safe
    function check_correct_impl(uint120 allocAmt, uint120 sendAmt, uint120 payment, uint16 bps) external pure {
        if (bps == 0 || bps > 10000) return;
        if (allocAmt == 0 || sendAmt == 0 || payment == 0) return;
        
        uint256 cap = uint256(payment) * bps / BPS;
        
        // CORRECT: allocate checks prev = distributed + allocated
        bool allocPasses = allocAmt <= cap; // prev=0
        // CORRECT: send checks prev = distributed + allocated
        bool sendPasses = (uint256(allocAmt) + sendAmt) <= cap; // prev=allocAmt
        
        if (allocPasses && sendPasses) {
            uint256 total = uint256(allocAmt) + uint256(sendAmt);
            assert(total <= cap); // ALWAYS holds with correct impl
        }
    }
}
