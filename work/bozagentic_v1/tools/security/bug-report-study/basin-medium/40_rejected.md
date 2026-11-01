# #40: Bored wells can receive Ether despite lack of any rescue functionality
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/libraries/LibClone.sol#L16


# Vulnerability details

In line with the fact that wells handle ERC-20s and not Ether, `Well.sol` does not implement any payable function. However, the chosen `LibClone.sol` implementation adds a `receive()` function that accepts Ether, also with as little gas as a `transfer` allows for.

## Impact
Any Ether accidentally transferred to a bored well will be accepted by the contract and remain frozen for good.

## Proof of Concept
The following test added to `Well.Bore.t.sol` passes, while it should fail:
```
    function test_receives_ether() public {
        vm.deal(user, 1 ether);
        vm.prank(user);
        (payable(address(well))).transfer(1 ether);
    }
```

## Tools Used
Manual review

## Recommended Mitigation Steps
One of the following:
- change the Clone implementation to one that does not expose a `receive()` function
- add a rescue function for stuck Ether


## Assessed type

ETH-Transfer