# #16: Critical slots being overwritten by bad designed _getSlotForAddress function
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/pumps/MultiFlowPump.sol#L336


# Vulnerability details

## Impact
A call to the `update` function (see my prev submission) with custom parameters and being called by a contract deployed to a custom address (see `CREATE2` and deterministic deployments) could overwrite critical slots in storage by manipulating the `msg.sender` address

## Proof of Concept
I am not gonna expand on the lack of access control in the `update` function (prev subm). The issue here is given by the `_getSlotForAddress` function (seriously, why not use storage the standard way)

```
function _getSlotForAddress(address addressValue) internal pure returns (bytes32) {
        return bytes32(bytes20(addressValue)); // Because right padded, no collision on adjacent
}
```

which is called with a "user-controlled" parameter in some places BUT the only place which writes to storage is the `update` function (the other are views which can return bad results, I may report that as QA, IDK). Anyway, if we call the `update` function from a contract deployed by deterministic methods (CREATE2 opcode), say, for the shake of the example, to very low level addresses 0x000000000...2 and so on, we could trick the `slot` variable and start overwriting variables from there with the values on `reserves`

## Tools Used
Manual analysis

## Recommended Mitigation Steps
Do not use `msg.sender` as a value to calculate slots, use storage like everyone else (through state variable in the contract, `storage` references, `sstore`s and all of that) and add access control to the `update` function (prev subm)


## Assessed type

Other