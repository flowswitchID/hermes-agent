# OracleBase Blacklist Bypass via Permissionless register()

## Severity: MEDIUM

## Summary

The `OracleBase.register()` function is permissionless (callable by anyone with 1 wei) and unconditionally clears the blacklist status of any pool. This allows an unprivileged attacker to defeat the admin's emergency blacklist — a critical security control that halts oracle access for compromised pools.

## Vulnerability Details

**File:** `smart-contracts-poc/contracts/oracles/providers/OracleBase.sol`
**Function:** `register()` (lines 201-213)

```solidity
function register(bytes32 feedId, address pool, address factory) external payable {
    require(msg.value >= registrationFee, InsufficientFee(msg.value, registrationFee));
    require(pool != address(0));
    require(approvedFactories.contains(factory), FactoryNotApproved(factory));
    require(IPoolFactory(factory).isPool(pool), NotAPool(pool));

    if (blacklisted[pool]) {
        blacklisted[pool] = false;  // ← ANYONE can clear blacklist
        emit BlacklistUpdated(pool, false);
    }

    registeredPool[feedId][pool] = true;
    emit PoolRegistered(feedId, pool, msg.sender, msg.value);
}
```

**Root cause:** `register()` has no access control modifier. Any external caller can invoke it with 1 wei (the default `registrationFee`) and clear the blacklist on any pool that belongs to an approved factory.

**The blacklist is a security-critical control:**
- `price()` (line 160-172) checks `notBlacklisted` modifier AND `require(!blacklisted[pool])`
- When a pool is blacklisted, it **cannot read oracle prices** → all swaps halt
- This is the admin's emergency response to compromised pools
- The Q&A states: *"Oracle ADMIN_ROLE — trusted. Blacklist, integrators, approved factories, registration fee, withdrawEth."*

**The bypass is trivial:**
1. `register()` is `external payable` with no access control
2. Cost: 1 wei (default `registrationFee`)
3. Pool must be from an approved factory (publicly known)
4. FeedId can be the same one the pool already uses
5. Blacklist is cleared regardless of whether pool is already registered

## Attack Scenario

1. Pool X has a vulnerability (e.g., extension bug, oracle manipulation)
2. Admin detects the issue → calls `setBlacklist(poolX, true)` (ADMIN_ROLE)
3. Pool X can no longer call `price()` → all swaps halt → users' funds protected
4. **Attacker calls `register(feedId, poolX, factory)` with 1 wei**
5. `blacklisted[poolX]` is set to `false`
6. Pool X can read oracle prices again → swaps resume
7. Attacker exploits the original vulnerability
8. Admin re-blacklists → attacker re-registers → **infinite loop**
9. Admin's emergency response is permanently defeated

**Race condition:** The attacker can monitor the mempool and front-run the admin's `setBlacklist()` transaction with `register()`, making re-blacklisting futile.

## Impact

- Admin's emergency security control (blacklist) is defeated by any unprivileged party
- Compromised pools can be forced back online against admin's wishes
- Users who should be protected by the blacklist remain exposed
- The invariant *"No trade on bad oracle"* (from Q&A) is violated
- Cost to attacker: 1 wei per bypass (economically trivial)

## Recommendation

Remove the blacklist-clearing logic from `register()`, or gate it behind `ADMIN_ROLE`:

```solidity
// Option A: Remove blacklist clearing from register()
function register(bytes32 feedId, address pool, address factory) external payable {
    require(msg.value >= registrationFee, InsufficientFee(msg.value, registrationFee));
    require(pool != address(0));
    require(approvedFactories.contains(factory), FactoryNotApproved(factory));
    require(IPoolFactory(factory).isPool(pool), NotAPool(pool));
    require(!blacklisted[pool], Blacklisted(pool)); // reject blacklisted pools

    registeredPool[feedId][pool] = true;
    emit PoolRegistered(feedId, pool, msg.sender, msg.value);
}

// Option B: Separate unblacklist function with ADMIN_ROLE
function unblacklist(address pool) external onlyRole(ADMIN_ROLE) {
    blacklisted[pool] = false;
    emit BlacklistUpdated(pool, false);
}
```

## Proof of Concept

See `BlacklistBypassPoC.t.sol` in the `poc/` directory.

Run:
```bash
forge test --match-contract BlacklistBypassPoC -vvv
```
