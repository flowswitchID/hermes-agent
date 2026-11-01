# #51: `CLOCK_EXTENSION` logic does not account for LPP `CHALLENGE_PERIOD`
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', 'upgraded by judge', ':robot:_34_group', 'duplicate-29']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/dispute/FaultDisputeGame.sol#L371-L382
https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L656-L657


# Vulnerability details


## Impact

In the `FaultDisputeGame` contract, the `CLOCK_EXTENSION` variable is the minimum amount of time a player has to respond to any follow-up claims. On OP mainnet, this time is currently set to 3 hours.

While this is helpful for honest users who might run low on time, it is especially important for addressing "freeloader claims." These are malicious claims that don't attempt to change the game's outcome, but aim to reclaim bond payments by remaining unchallenged. As described in [the OP docs](https://specs.optimism.io/fault-proof/stage-one/fault-dispute-game.html#freeloader-claims), "the honest challenger must always counter freeloader claims for incentive compatibility to be preserved." Since countering a freeloader claim means inheriting the adversary's clock, honest users must be capable of relying on just the `CLOCK_EXTENSION` timeline, even if they always act immediately.

In addition to the `CLOCK_EXTENSION`, the `PreimageOracle` contract introduces another important variable, the `CHALLENGE_PERIOD`. This variable is the minimum waiting time for potential challenges before a large preimage proposal (LPP) can be confirmed. On OP mainnet, this time is currently set to 24 hours.

When considered together, these two mechanisms can create a problem. An honest user is expected to always be capable of responding to claims within 3 hours, but may also need to wait 24 hours before a necessary LPP can be confirmed for a `step()` resolution. There are two potential counterarguments to this issue:

1. The `loadKeccak256PreimagePart()` function provides an alternative method of proving keccak256 preimages without requiring the `CHALLENGE_PERIOD` wait. However, it can be shown that the op-program can request preimages large enough that `loadKeccak256PreimagePart()` would exceed the L1 block gas limit. For example, [notice that op-program can request transaction receipt hash preimages](https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/op-program/client/l1/oracle.go#L81-L97), which can have an extremely large size for transactions that log a lot of data.


2. If an honest user anticipates that an LPP may be needed, they can initiate the LPP before the final `step()`. However, this isn't currently implemented in op-challenger, [which only considers `OracleData` if the next move is a `step()`](https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/op-challenger/game/fault/solver/game_solver.go#L57-L115). Moreover, multiple possible LPP preimages could be reachable within 24 hours of the game ending, making it unrealistic for the honest user to preload all of them.

    _Technical note: This is especially true because each individual offset requires a new LPP, and data is only read in chunks of 4 bytes. Additionally, some modifications to the `cannon/` code revealed that each 4-byte read is split by about 1200 steps in `MIPS.sol`. Therefore, a player that has 8 moves left (which is 8 * 3 = 24 hours) compared to their adversary's 7 remaining moves, can have `(2 ** 15) / 1200 = 27` different possible LPP that can be reached within 24 hours of the game ending._

So, in summary, an honest user can find themselves in a situation where they time-out of a `CLOCK_EXTENSION` due to the LPP challenge period. Even if the user always makes movements instantly, "freeloader claims" can force a user into a low-time situation. If a user times-out before they can `step()`, they can fail to disprove an invalid claim, which would either allow an invalid state transition or result in the honest user losing a large bond. 

## Proof of Concept

The following changes can be made within `op-e2e/e2eutils/disputegame/output_game_helper.go`:

```diff
func (g *OutputGameHelper) DisputeBlock(ctx context.Context, disputeBlockNum uint64) *ClaimHelper {
    // ...

+   i := 0
    claim := g.RootClaim(ctx)
    for !claim.IsOutputRootLeaf(ctx) {
+       if i == 0 || i == 1 {
+           g.System.AdvanceTime(time.Duration(1040) * time.Second)
+       }
+       i += 1
        parentClaimBlockNum, err := g.CorrectOutputProvider.ClaimedBlockNumber(pos)
        g.Require.NoError(err, "failed to calculate parent claim block number")
        if parentClaimBlockNum >= disputeBlockNum {
            pos = pos.Attack()
            claim = claim.Attack(ctx, getClaimValue(claim, pos))
        } else {
            pos = pos.Defend()
            claim = claim.Defend(ctx, getClaimValue(claim, pos))
        }
    }
    return claim
}

// ...

func (g *OutputGameHelper) GameData(ctx context.Context) string {
    // ...
    for i, claim := range claims {
        pos := claim.Position
	    extra := ""
	    if pos.Depth() <= splitDepth {
	        blockNum, err := g.CorrectOutputProvider.ClaimedBlockNumber(pos)
		    if err != nil {
		    } else {
			extra = fmt.Sprintf("Block num: %v", blockNum)
		    }
	    }
-           info = info + fmt.Sprintf("%v - Position: %v, Depth: %v, IndexAtDepth: %v Trace Index: %v, ClaimHash: %v, Countered By: %v, ParentIndex: %v Claimant: %v Bond: %v %v\n",
-	        i, claim.Position.ToGIndex().Int64(), pos.Depth(), pos.IndexAtDepth(), pos.TraceIndex(maxDepth), claim.Value.Hex(), claim.CounteredBy, claim.ParentContractIndex, claim.Claimant, claim.Bond, extra)
+           info = info + fmt.Sprintf("%v - Position: %v, Depth: %v, Clock duration: %v, Clock timestamp: %v, IndexAtDepth: %v Trace Index: %v, ClaimHash: %v, Countered By: %v, ParentIndex: %v Claimant: %v Bond: %v %v\n",
+               i, claim.Position.ToGIndex().Int64(), pos.Depth(), claim.Clock.Duration, claim.Clock.Timestamp, pos.IndexAtDepth(), pos.TraceIndex(maxDepth), claim.Value.Hex(), claim.CounteredBy, claim.ParentContractIndex, claim.Claimant, claim.Bond, extra)
    }
    // ...
}
```


And the following change can be made to the devnet deployment config:

```diff
// Changes specifically made to these files: 
//     - `packages/contracts-bedrock/deploy-config/devnetL1-template.json`
//     - `packages/contracts-bedrock/scripts/getting-started/config.sh`
{
    // ...
-   "faultGameClockExtension": 0,
+   "faultGameClockExtension": 100,
    // ...
}

// Also this seems to require the following change to `packages/contracts-bedrock/scripts/Deploy.s.sol` for the build to succeed:
function setFastFaultGameImplementation(
    // ...
-   maxClockDuration: Duration.wrap(0)
+   maxClockDuration: Duration.wrap(1200)
    // ...
)
```


These changes will add a delay to both sides of the dispute game before the challenger begins disputing. Also, these changes make the `CLOCK_EXTENSION` 100 seconds, which is shorter than the 120 second `CHALLENGE_PERIOD` in the tests.


After rebuilding with these modifications, the existing `TestOutputCannonStepWithLargePreimage` test case can be run with `go test ./faultproofs -run TestOutputCannonStepWithLargePreimage -v -timeout=60m > test_output.txt`. The output can be inspected with the following:

```
> grep "50 - Position:" -B 1 test_output.txt; grep "Error:" -A 1 test_output.txt
        49 - Position: 562949987800306, Depth: 49, Clock duration: 18m20s, Clock timestamp: 2024-07-29 14:41:12 -0400 EDT, IndexAtDepth: 34378994 Trace Index: 68757989, ClaimHash: 0x034e1933a0f124e565f896d54ccba4ee127e190b710c4cae57619b202fca6104, Countered By: 0x0000000000000000000000000000000000000000, ParentIndex: 48 Claimant: 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65 Bond: 52559354600000000000 
        50 - Position: 1125899975600614, Depth: 50, Clock duration: 18m20s, Clock timestamp: 2024-07-29 14:41:14 -0400 EDT, IndexAtDepth: 68757990 Trace Index: 68757990, ClaimHash: 0xcc00000000000000000000000000000000000000000000000000000000000000, Countered By: 0x0000000000000000000000000000000000000000, ParentIndex: 49 Claimant: 0x71562b71999873DB5b286dF957af199Ec94617F7 Bond: 59999999800000000000 
                Error:          Received unexpected error:
                                context deadline exceeded
```

Ultimately, this shows that the challenger enters into a dispute game where they eventually only have 100 seconds in each response (18m20s duration). They eventually fail to respond to the final claim, because they wait 120 seconds for the LPP deadline and time-out. This results in the entire dispute failing.

## Tools Used

The op-e2e test suite.

## Recommended Mitigation Steps

Add `CHALLENGE_PERIOD` seconds onto the `CLOCK_EXTENSION` when a potential grandchild claim involves a `step()`:

```solidity
uint64 extensionPeriod = CLOCK_EXTENSION.raw();
// If the potential grandchild is an execution trace bisection root, double the clock extension.
if (nextPositionDepth == SPLIT_DEPTH - 1) {
    extensionPeriod = CLOCK_EXTENSION.raw() * 2;
}
// If the potential grandchild is an execution trace `step()`, account for a possible LPP challenge period.
if (nextPositionDepth == MAX_GAME_DEPTH - 1) {
    extensionPeriod += VM.oracle().challengePeriod();
}
```


## Assessed type

Other