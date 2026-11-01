# #26: An attacker can take the bond away from the honest challenger if `FDG.CLOCK_EXTENSION` is less than `PreimageOracle.CHALLENGE_PERIOD`
Labels: ['bug', '3 (High Risk)', 'partial-75', 'sufficient quality report', 'upgraded by judge', 'edited-by-warden', ':robot:_primary', ':robot:_34_group', 'duplicate-29']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L657
https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/dispute/FaultDisputeGame.sol#L371-L382


# Vulnerability details

Large preimage proposals (LPP) allow submitters to prove that certain data is a fixed part of the large preimage that produces a specific Keccak-256 hash value. Since the preimage is large, the process of LPP finalization involves multiple transactions. Because the intermediate steps are not verified on-chain, LPP flow requires a challenge period during which the proposal can't be finalized. In another issue, I've demonstrated that it is possible to finalize prematurely, but here we'll assume that the LPP flow is not broken.

To demonstrate this issue, let's consider a scenario where an attacker makes a freeloader claim at the depth `MAX_GAME_DEPTH`. In the worst case, honest challengers will have `FDG.CLOCK_EXTENSION` time to counter this move by calling the `step` function. The issue arises if this call requires a finalized LPP proposal. As mentioned earlier, the process of LPP finalization is not immediate and requires `PreimageOracle.CHALLENGE_PERIOD` to pass. If the `FDG.CLOCK_EXTENSION` is less than `PreimageOracle.CHALLENGE_PERIOD`, honest challengers will be unable to counter the freeloader claim since they cannot finalize the LPP proposal before the clock expires. This essentially means that a malicious actor can take the bond away from the honest challenger.

If we consider the current values of these parameters on mainnet, we'll see that this attack is possible with the current configuration:
```
CHALLENGE_PERIOD=86400 
CLOCK_EXTENSION=10800
```

## Impact
An attacker can take the bond away from the honest challenger.

## Proof of Concept
\-

## Tools Used
Manual Review

## Recommended Mitigation Steps
Ensure that honest challengers have enough time to finalize LPP to counter freeloader claims.





## Assessed type

Timing