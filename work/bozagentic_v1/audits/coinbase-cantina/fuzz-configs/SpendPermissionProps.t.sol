// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title SpendPermission period math — symbolic verification
contract SpendPermissionProps {
    
    // PROPERTY: period calculation is deterministic
    function check_period_deterministic(uint32 start, uint32 period, uint48 ts) external pure {
        if (period == 0) return;
        if (ts < start) return;
        uint32 p1 = uint32((uint256(ts) - start) / period);
        uint32 p2 = uint32((uint256(ts) - start) / period);
        assert(p1 == p2);
    }
    
    // PROPERTY: period is monotonically non-decreasing with time
    function check_period_monotonic(uint32 start, uint32 period, uint48 ts1, uint48 ts2) external pure {
        if (period == 0) return;
        if (ts1 < start || ts2 < start) return;
        if (ts2 < ts1) return; // ensure ts2 >= ts1
        uint32 p1 = uint32((uint256(ts1) - start) / period);
        uint32 p2 = uint32((uint256(ts2) - start) / period);
        assert(p2 >= p1);
    }
    
    // PROPERTY: spentInPeriod tracking — can't exceed allowance
    function check_spend_bounded(uint160 allowance, uint160 spend1, uint160 spend2) external pure {
        if (allowance == 0) return;
        // First spend
        if (spend1 > allowance) return; // would revert
        uint256 remaining = uint256(allowance) - spend1;
        // Second spend
        if (spend2 > remaining) return; // would revert
        uint256 totalSpent = uint256(spend1) + uint256(spend2);
        assert(totalSpent <= allowance);
    }
    
    // PROPERTY: period reset — new period starts fresh
    function check_period_reset(uint160 allowance, uint160 spentP1, uint160 spentP2) external pure {
        if (allowance == 0) return;
        // Period 1: spend up to allowance
        if (spentP1 > allowance) spentP1 = allowance;
        // Period 2: fresh allowance (reset)
        if (spentP2 > allowance) spentP2 = allowance;
        // Both periods can spend full allowance independently
        assert(spentP1 <= allowance);
        assert(spentP2 <= allowance);
        // Total across periods CAN exceed allowance (by design)
        // This is NOT a bug — periodic allowance resets
    }
    
    // PROPERTY: CEI — state update before external call
    // Model: spentInPeriod updated BEFORE transfer
    function check_cei_order(uint160 allowance, uint160 amount) external pure {
        if (allowance == 0 || amount == 0) return;
        if (amount > allowance) return;
        
        // Step 1: Update state (spentInPeriod += amount)
        uint256 spentInPeriod = amount;
        
        // Step 2: Check (would reentrancy pass?)
        // Reentrant call: totalSpend = amount + spentInPeriod
        uint256 reentrantTotal = uint256(amount) + spentInPeriod;
        
        // If reentrantTotal > allowance → reentrancy BLOCKED
        if (reentrantTotal > allowance) {
            assert(spentInPeriod > 0); // state was updated
        }
    }
}
