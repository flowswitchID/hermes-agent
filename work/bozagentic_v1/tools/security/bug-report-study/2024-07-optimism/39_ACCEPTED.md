# #39: Improper proof validation causes incorrect resolution of step
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_primary']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/dispute/FaultDisputeGame.sol#L302


# Vulnerability details

## Impact
Incorrect resolution of dispute game - True claim can be resolved as False

## Proof of Concept
When stepping, `proof` data that represents VM's memory is provided along with data.
Each slot takes 28 * 32bytes of data, 32bytes for data(leaf) and 27 * 32bytes for merkle proof.

The slot0 of proof indicates the PC(Program Counter) of the VM.
There might exist slot1 based on the opcode. If the opcode is related to memory load, slot0 represents the memory to load.
Or if the opcode is related to memory write, slot1 represents the memory to overwrite.

The validity of data of slot0 and slot1 are guaranteed my `memRoot` field of stateData which is validated.
However, even though slot0 and slot1 satisfy `memRoot`, it does not guarantee if the memory data is correct.

For example, here's an attack scenario, where an attacker can mess up with memory to make invalid step.

1. Assume the root claim is valid.
2. A malicious attacker finds a random block and get one memory read instruction leaf.
3. It's assumed that the instruction leaf is the right child.
4. The attacker makes a defend step at the end.
5. The attacker passes slot0 data into slot1 data(or get any other memory and its proof that satisfies `memRoot`).
6. Since the slot1 data is incorrect, calculated `postState` can't be same as assumed `postState`.
7. As a result, the attacker can count the leaf and make the opposite resolution of the game

## Tools Used
Manual Review

## Recommended Mitigation Steps
When constructing memory slots, address of memory should be put together with memory data to construct hash of the leaves, so that when `readMem` is called, it should validate if `slot1` has correct address data.

```diff
    function readMem(uint32 _addr, uint8 _proofIndex) internal pure returns (uint32 out_) {
        unchecked {
            // Compute the offset of the proof in the calldata.
            uint256 offset = proofOffset(_proofIndex);

            assembly {
                // Validate the address alignement.
                if and(_addr, 3) { revert(0, 0) }

                // Load the leaf value.
                let leaf := calldataload(offset)
                offset := add(offset, 32)

+               // Load the memory address
+               let memAddr = calldataload(oofset)
+               offset := add(offset, 32)
+
+               let addrStart = _addr & 31; // Start of 32bytes memory
+               if iszero(eq(addrStart, memAddr)) { revert(0, 0) }

                // Convenience function to hash two nodes together in scratch space.
                function hashPair(a, b) -> h {
                    mstore(0, a)
                    mstore(32, b)
                    h := keccak256(0, 64)
                }

+               leaf := hashPair(leaf, memAddr)

                // Start with the leaf node.
                // Work back up by combining with siblings, to reconstruct the root.
                let path := shr(5, _addr)
                let node := leaf
                for { let i := 0 } lt(i, 27) { i := add(i, 1) } {
                    let sibling := calldataload(offset)
                    offset := add(offset, 32)
                    switch and(shr(i, path), 1)
                    case 0 { node := hashPair(node, sibling) }
                    case 1 { node := hashPair(sibling, node) }
                }

                // Load the memory root from the first field of state.
                let memRoot := mload(0x80)

                // Verify the root matches.
                if iszero(eq(node, memRoot)) {
                    mstore(0, 0x0badf00d)
                    revert(0, 32)
                }

                // Bits to shift = (32 - 4 - (addr % 32)) * 8
                let shamt := shl(3, sub(sub(32, 4), and(_addr, 31)))
                out_ := and(shr(shamt, leaf), 0xFFffFFff)
            }
        }
    }
```

Also `proofOffset` function should be modified to ensure each slot takes 29 * 32bytes.


## Assessed type

Context