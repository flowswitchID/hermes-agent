# #35: Calling beginEra() in the StRSR initializer will incorrectly reset state variables
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', ':robot:_primary']
Accepted: False

# Lines of code

https://github.com/reserve-protocol/protocol/blob/master/contracts/p1/StRSR.sol#L201
https://github.com/reserve-protocol/protocol/blob/master/contracts/p1/StRSR.sol#L671
https://github.com/reserve-protocol/protocol/blob/master/contracts/p1/StRSR.sol#L683


# Vulnerability details

## Impact
The initializer function in StRSR.sol incorrectly bundles a call to `beginEra()`. This will incorrectly reset the era back to 1, reverting user funds to that state and reset the stakeRSR and totalStakes variables to 0 and will lead to loss of funds.

## Proof of Concept
As of writing of this report, the [proxy contract](https://etherscan.io/address/0x18ba6e33ceb80f077DEb9260c9111e62f21aE7B8) of the StRSR contract holds ~ 17,000 USD in tokens. The contract is well in use and thus the `stakeRSR` and `totalStakes` variables are non-zero. The StRSR.sol contract bundles a call to `beginEra()` and beginDraftEra in it's intializer function:

https://github.com/reserve-protocol/protocol/blob/master/contracts/p1/StRSR.sol#L201
```js
    function init(
        ...
    ) external initializer {
        ...
        beginEra();
        beginDraftEra();
    }
```

Both of these calls will incorrectly reset critical state variables to 0, breaking the accounting of the protocol and putting user funds at risk.

https://github.com/reserve-protocol/protocol/blob/master/contracts/p1/StRSR.sol#L671
```js
    function beginEra() internal virtual {
        stakeRSR = 0;
        totalStakes = 0;
        stakeRate = FIX_ONE;
        era++;

        emit AllBalancesReset(era);
    }
```

https://github.com/reserve-protocol/protocol/blob/master/contracts/p1/StRSR.sol#L683
```js
    function beginDraftEra() internal virtual {
        draftRSR = 0;
        totalDrafts = 0;
        draftRate = FIX_ONE;
        draftEra++;

        emit AllUnstakingReset(draftEra);
    }
```
The era should not be tied to the contract being updated, it should only really be called when the proxy contract is initialized for the very first time. Any subsequent intialization during upgrade of the proxy contract should have the beginEra call removed from the initializer. 

## Tools Used
Manual Review

## Recommended Mitigation Steps
Remove the call to `beginEra()` from the initializer and instead bundle it in the deployment script for that particular version of the contract.


## Assessed type

Upgradable