# #79: Well.sol - flashloan liquidity manipulation can lead to a DoS of user transactions and potential drainage of pool tokens
Labels: ['bug', '2 (Med Risk)', 'downgraded by judge', 'satisfactory', 'sponsor disputed', 'duplicate-255']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L215-L240
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ConstantProduct2.sol#L49-L54
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ConstantProduct2.sol#L58-L75


# Vulnerability details

## Details
The swapping mechanism of a Well using the ``ConstantProduct2.sol`` as it's function is susceptible to a flashloan attack to drain pool tokens, or to a combination of a flashloan + sandwich attack to DoS user swaps.

## Impact
A malicious actor can drain tokens by creating his own arbitrage with a flashloan, or he can DoS user swaps to effectively freeze swaps under certain conditions, which are realistic. Check POC for more details.

## Proof of Concept
Let us define a basic 2 token Well, that implements the CP2 function (for simplicity's sake).
TOKEN A - reserve = 10_000
TOKEN B - reserve = 10_000
With these values, the LP token supply would be 10_000 as well (the square root of 100 million)

#### The flashloan + sandwich DoS scenario:
Alice wants to swap 1000 of tokenA to tokenB so she uses ``_swapFrom()`` and for a min amount she inputs a value i n the range of [100:900].
###### In the default scenario the tx will go as follows:
reserveA = 11_000
reserveB = _calcReserve (from the CP2) = LP supply ** 2 / reserveA = 100mill / 11_000 = 9090
This means that the amount out Alice would get is 910 which satisfies the minAmountOut, no matter what value in the specified range it is.
A malicious actor can use a flashloan (or even his own balance depending on the ``minAmountOut``) to add liquidity to tokenA and greatly decrease the amount Alice would receive by front-running her.
###### Malicious scenario:
reserveA after flashloan frontrun + Alice's input: 10_000 + 100_000 + 1_000(after Alice)
reserveB = _calcReserve = LP supply ** 2 / reserveA = 10_000(reserveBbefore) * reserveA(before Alice) / reserveA =  1_010_000_000 / 111_000 = 9099
This means that the amount out Alice would get is only 101 which can fail is some cases due to the slippage check done. The amount get's even lower for greater pumps.

#### The flashloan + arbitrage drainage scenario:
A malicious actor uses a flashloan to produce a similiar pump to the one mentioned above, but he does it in reverse, aka:
reserveA = 10_000
reserveB after flashloan liquidity pump = 10_000 + 100_000
LP supply ** 2 right now is: 1_100_000_000
He begins a regular transaction from A to B, by adding 1000 A tokens so reserveA = 10_000 + 1_000
reserveB now changes as follow: _calcReserve = 1_100_000_000 / 11_000 = 100_000
This means that the actor managed to take out 10K of token B for just 1K token A, effectively draining the currently defined pool when he removes his liquidity to pay back the flashloan.

## Tools Used
Manual Review

## Recommended Mitigation Steps
There should be a default mechanism implemented, such as that even non-maliciously defined Well's that are verified by the protocol team as 'innocent' aren't susceptible to such high reserve movements. You could do a number of things like:

 1. A limit on liquidity adding, so that amounts do not get this greatly manipulated
 2. A snapshot-like mechanism to check the reserves at which the current tx is being calculated compared to the previous one (or from a previous block where the flashloan hasn't happened yet)
 


## Assessed type

Math