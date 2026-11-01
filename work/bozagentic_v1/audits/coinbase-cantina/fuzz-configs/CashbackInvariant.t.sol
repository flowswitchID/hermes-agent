// SPDX-License-Identifier: MIT
pragma solidity ^0.8.29;

/// @title Invariant test that would catch the maxRewardBps bypass
/// @notice This demonstrates how to write targeted invariants
/// 
/// The invariant: for any payment, allocated + distributed <= maxAllowed
/// If this invariant BREAKS, the cap is bypassed.
///
/// In the buggy code:
///   allocate(cap) → allocated = cap, distributed = 0 → total = cap ✅
///   send(cap)     → distributed = cap, allocated = cap → total = 2*cap ❌
///
/// This invariant would FAIL after the second operation,
/// proving the bug exists.

contract CashbackInvariantModel {
    // Model the CashbackRewards state
    uint120 public allocated;
    uint120 public distributed;
    uint120 public maxAllowed;
    
    constructor() {
        // Setup: payment = 10000, bps = 5000 (50%)
        maxAllowed = 5000;
    }
    
    // Simulate ALLOCATE operation
    function allocate(uint120 amount) external {
        if (amount == 0) return;
        // Buggy validation: prev = distributed + allocated
        uint120 prev = distributed + allocated;
        if (prev + amount > maxAllowed) return; // would revert
        allocated += amount;
    }
    
    // Simulate SEND operation (BUGGY: ignores allocated)
    function sendBuggy(uint120 amount) external {
        if (amount == 0) return;
        // BUG: prev = distributed ONLY (ignores allocated!)
        uint120 prev = distributed;
        if (prev + amount > maxAllowed) return; // would revert
        distributed += amount;
    }
    
    // Simulate SEND operation (CORRECT: counts allocated)
    function sendCorrect(uint120 amount) external {
        if (amount == 0) return;
        // CORRECT: prev = distributed + allocated
        uint120 prev = distributed + allocated;
        if (prev + amount > maxAllowed) return; // would revert
        distributed += amount;
    }
    
    // Simulate DEALLOCATE
    function deallocate(uint120 amount) external {
        if (amount > allocated) amount = allocated;
        allocated -= amount;
    }
    
    // Simulate DISTRIBUTE (shift allocated → distributed)
    function distribute(uint120 amount) external {
        if (amount > allocated) return;
        // BUG: same as send — ignores allocated in cap check
        uint120 prev = distributed;
        if (prev + amount > maxAllowed) return;
        allocated -= amount;
        distributed += amount;
    }
    
    // INVARIANT: total rewarded should never exceed cap
    // This WILL FAIL with buggy send/distribute
    function echidna_cap_invariant() external view returns (bool) {
        return uint256(allocated) + uint256(distributed) <= maxAllowed;
    }
    
    // INVARIANT: distributed alone should never exceed cap
    function echidna_distributed_bounded() external view returns (bool) {
        return distributed <= maxAllowed;
    }
}
