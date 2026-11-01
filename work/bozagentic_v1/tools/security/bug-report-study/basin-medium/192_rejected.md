# #192: No fee swap is possible through `addLiquidity` and `removeLiquidityImbalanced`
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L413-L444
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L495-L517


# Vulnerability details

## impact
Some will not pay swap fees even after the swap fee is added.

## proof of concept
This is equivalent to swap 1000 tokenA to 500 tokenB, but no fee calculation code lies in adding and removing liquidity.
Add this test in `Well.AddLiquidity.t.sol`.
```solidity
function test_zeroFeeSwap() public {
    uint256[] memory amounts0 = new uint256[](tokens.length);
    amounts0[0] = 1000e18;

    uint256[] memory amounts1 = new uint256[](tokens.length);
    amounts1[1] = 500e18;

    vm.prank(user);
    well.addLiquidity(amounts0, 0, user, type(uint256).max);

    vm.prank(user);
    well.removeLiquidityImbalanced(type(uint256).max, amounts1, user, type(uint256).max);
}
```

The sponsor, hellofromguy said they can add fee later, but the current implementation is hard to add.
> Just to be clear, a Well function can have a trading fee. But ConstantProduct2.sol, the Well function that we have implemented and that is in scope, does not.
https://discord.com/channels/810916927919620096/1124366470349066290/1125990724748455986

## tools used
Manual review.

## recommended mitigation steps
1. For now, add a state variable `swapFee` and set it to 0. Charge fee on every imbalanced addLiquidity and removeLiquidity.
2. Set `swapFee` to nonzero when swap fee is added to ConstantProduct2.


## Assessed type

Other