// SPDX-License-Identifier: MIT
pragma solidity ^0.8.29;

/// @title Echidna sequence test: model the full CashbackRewards lifecycle
/// @notice Tests: allocate → distribute → send → deallocate sequences
contract CashbackSequence {
    uint120 public allocated;
    uint120 public distributed;
    uint120 public constant CAP = 50_000;
    uint120 public constant PAYMENT = 100_000;
    uint256 public constant BPS = 5000;
    
    // Model: allocate operation
    function allocate(uint120 amount) external {
        if (amount == 0) return;
        // Buggy validation: prev = distributed + allocated (correct for ALLOCATE)
        uint120 prev = distributed + allocated;
        uint120 cap = uint120(uint256(PAYMENT) * BPS / 10000);
        if (prev + amount > cap) return; // would revert
        allocated += amount;
    }
    
    // Model: send operation (BUGGY — ignores allocated)
    function sendBuggy(uint120 amount) external {
        if (amount == 0) return;
        uint120 prev = distributed; // BUG: ignores allocated!
        uint120 cap = uint120(uint256(PAYMENT) * BPS / 10000);
        if (prev + amount > cap) return;
        distributed += amount;
    }
    
    // Model: distribute (shift allocated → distributed)
    function distribute(uint120 amount) external {
        if (amount == 0) return;
        if (amount > allocated) return;
        // Buggy validation: prev = distributed (ignores allocated)
        uint120 prev = distributed;
        uint120 cap = uint120(uint256(PAYMENT) * BPS / 10000);
        if (prev + amount > cap) return;
        allocated -= amount;
        distributed += amount;
    }
    
    // Model: deallocate (always allowed, skips cap check)
    function deallocate(uint120 amount) external {
        if (amount == 0) return;
        if (amount > allocated) amount = allocated;
        allocated -= amount;
    }
    
    // INVARIANT: total rewarded should never exceed cap
    function echidna_cap_invariant() external view returns (bool) {
        return uint256(allocated) + uint256(distributed) <= CAP;
    }
    
    // INVARIANT: distributed should never exceed cap alone
    function echidna_distributed_bounded() external view returns (bool) {
        return distributed <= CAP;
    }
    
    // INVARIANT: allocated should never exceed cap alone
    function echidna_allocated_bounded() external view returns (bool) {
        return allocated <= CAP;
    }
}
