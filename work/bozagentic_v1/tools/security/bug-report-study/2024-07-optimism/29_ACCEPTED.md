# #29: The LPP challenge period can cause malicious and freeloader claims to be uncounterable and can also cause freeloader claims to be abused to entrap honest challengers
Labels: ['bug', '3 (High Risk)', 'primary issue', 'satisfactory', 'selected for report', 'sponsor confirmed', 'sufficient quality report', 'upgraded by judge', 'edited-by-warden', ':robot:_primary', ':robot:_34_group', 'H-02']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/main/packages/contracts-bedrock/src/dispute/FaultDisputeGame.sol#L371-L382


# Vulnerability details

In some cases, the honest challenger must pass an LPP in order to counter a `MAX_GAME_DEPTH` claim through `step()`. For instance, "in the event that the preimage is too large to be submitted through calldata in a single block, challengers must resort to the streaming option" as described in the Optimism [specs](https://specs.optimism.io/fault-proof/stage-one/fault-dispute-game.html?highlight=large%20preimage%20proposal#preimageoracle-interaction).

However, an issue arises because to pass an LPP, the honest challenger must wait for `CHALLENGE_PERIOD` seconds in order to pass the LPP to be able to `step()` against a malicious `MAX_GAME_DEPTH` claim. The honest challenger will have a minimum of one `CLOCK_EXTENSION` (3 hours on mainnet) period on their chess clock, which cannot cover the `CHALLENGE_PERIOD` for an LPP (1 day on mainnet).

There are essentially 3 impacts that this can cause:

### Impact 1: A malicious `MAX_GAME_DEPTH` claim can be uncounterable if honest challenger does not have time left

If the honest challenger has less than 1 day left in their chess clock when reaching the malicious claim at `MAX_GAME_DEPTH`, they cannot possibly pass an LPP in time. This will cause the malicious claim to be uncountered while the honest challenger's claim will be countered leading to an incorrect game result.

### Impact 2: Uncounterable freeloader claims can be made by forcing an honest challenger to inherit a clock smaller than `CHALLENGE_PERIOD`

The `CLOCK_EXTENSION` is a feature meant for honest challengers to counter a freeloader claim, a freeloader claim is described as follows:

Consider an attacker claim denoted by A in the subtree below. Suppose that this claim is valid, then the correct move for the honest party is to defend the claim. The honest party's claim is denoted by claim H.
```
   A  
 /   \
F     H
```
To prevent themselves from losing the bond, suppose the attacker then attacks claim A with the claim F. Due to the leftmost priority, they would receive the bond if their freeloader claim F remains uncountered. This is possible if the attacker's chess clock has very little time left because the honest party needs to use the attacker's chess clock to counter the freeloader claim. 

To resolve this, Optimism uses clock extensions, where if a chess clock has less than `CLOCK_EXTENSION` seconds left, it is extended to `CLOCK_EXTENSION` seconds.

If the honest challenger must pass an LPP to counter the freeloader claim at `MAX_GAME_DEPTH` via `step()` it will not have enough time to do so, resulting in the freeloader claim stealing the bond from the honest party's claim.

### Impact 3: Freeloader claims can now be used to bait honest challengers to respond and then entrap them, winning all the bonds they used to counter the freeloader claim

Combining the points raised in both impacts earlier, we can now see how freeloader claims can be used as bait to steal all the bonds used to counter the freeloader claim. The key point here is that when the honest challenger counters a freeloader claim, they essentially "swap" chess clocks with the attacker. All further moves made by the honest challenger now use the attacker's chess clock which can be manipulated to `CLOCK_EXTENSION` earlier. Now, let's take a look at the following scenario:

```
   A  
 /   \
F1    H1
|
H2
|
F2
```

Here, the attacker has responded to the honest user's claim H2, with their new claim F2. To counter F2, the honest challenger will still be using the attacker's chess clock which will be manipulated to `CLOCK_EXTENSION` time. Let's suppose F2 is a claim at `MAX_GAME_DEPTH` and to counter it the honest challenger must pass an LPP, as elaborated earlier they won't be able to do so and they essentially cannot counter F2. But now, they also will have their bonds for posting H2 stolen from them, as F2 will now counter H2. Furthermore, the freeloader claim F1 will still steal the bond from A using the leftmost priority.

Therefore, this technique can be used attackers to entrap honest challengers, by purposefully posting an invalid state that has a valid state preceding it that requires a max size LPP to execute `step()` on, they can further steal bonds away from the honest challengers to counter the freeloader claim.

## Tools Used
Code review

## Recommended Mitigation Steps

Apply a bigger extension such as `CHALLENGE_PERIOD + CLOCK_EXTENSION` at the `MAX_GAME_DEPTH - 1` claim, as shown below.
```diff
+       IPreimageOracle oracle = VM.oracle();
+       if (nextPositionDepth == MAX_GAME_DEPTH - 1 && nextDuration.raw() > MAX_CLOCK_DURATION.raw() - oracle.challengePeriod() - CLOCK_EXTENSION.raw()) {
+           // Apply 1 CHALLENGE_PERIOD + 1 CLOCK_EXTENSION here. 
+           nextDuration = Duration.wrap(MAX_CLOCK_DURATION.raw() - oracle.challengePeriod() - CLOCK_EXTENSION.raw());
+       }
+       else if (nextDuration.raw() > MAX_CLOCK_DURATION.raw() - CLOCK_EXTENSION.raw()) {
-       if (nextDuration.raw() > MAX_CLOCK_DURATION.raw() - CLOCK_EXTENSION.raw()) {
            // If the potential grandchild is an execution trace bisection root, double the clock extension.
            uint64 extensionPeriod =
                nextPositionDepth == SPLIT_DEPTH - 1 ? CLOCK_EXTENSION.raw() * 2 : CLOCK_EXTENSION.raw();
            nextDuration = Duration.wrap(MAX_CLOCK_DURATION.raw() - extensionPeriod);
        }

```

This will solve all of the scenarios above.









## Assessed type

Other