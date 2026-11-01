# #12: An invariant violation and revert in the FaultDisputeGame.step function
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_27_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/main/packages/contracts-bedrock/src/dispute/FaultDisputeGame.sol#L255


# Vulnerability details

## Impact
While the following code has a comment stating that the *invariant( is that the step that is getting submitted in `FaultDisputeGame.step` is unacceptable **unless** the move position is `1` ***below*** the `MAX_GAME_DEPTH`:
```solidity
        // INVARIANT: A step cannot be made unless the move position is 1 below the `MAX_GAME_DEPTH`
        if (stepPos.depth() != MAX_GAME_DEPTH + 1) revert InvalidParent();
```
, the actual assertion that is performed, *which if resolves to `true`, leads to a `revert InvalidParent();` error*, is that the move's depth (`stepPos.depth()`) is not `1` **ABOVE** the `MAX_GAME_DEPTH`.

Which means that the `MAX_GAME_DEPTH` can be exceeded by `1`.

And also that if the `stepPos.depth()` is `!=` `MAX_GAME_DEPTH`, then there'll be a revert.

It will not revert if the `stepPos.depth() == MAX_GAME_DEPTH`.

## Proof of Concept
I believe that if the invariant is correctly described in the comment, the PoC is likely redundant.

## Tools Used
Manual review.

## Recommended Mitigation Steps
I humbly believe that the proper way to assert the condition stated in the invariant annotation's comment is the following:
```diff
        // INVARIANT: A step cannot be made unless the move position is 1 below the `MAX_GAME_DEPTH`
-       if (stepPos.depth() != MAX_GAME_DEPTH + 1) revert InvalidParent();
+       if (stepPos.depth() != MAX_GAME_DEPTH - 1) revert InvalidParent();
```

Or maybe:
```diff
        // INVARIANT: A step cannot be made unless the move position is 1 below the `MAX_GAME_DEPTH`
-       if (stepPos.depth() != MAX_GAME_DEPTH + 1) revert InvalidParent();
+       if (stepPos.depth() <= MAX_GAME_DEPTH - 1) revert InvalidParent();
```


## Assessed type

DoS