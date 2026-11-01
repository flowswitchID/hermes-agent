# #146: Stealing excess tokens from other users by either front-running `skim` function or calling it before legitimate user
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-291']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L603-L613


# Vulnerability details

## Impact

File `/src/interfaces/IWell.sol` comment's defines what the `skim` function is being responsible for:

```
 /**
     * @notice Sends excess tokens held by the Well to the `recipient`.
     * @param recipient The address to send the tokens
     * @return skimAmounts The amount of each token skimmed
     */
    function skim(address recipient) external returns (uint256[] memory skimAmounts);
```

After more comprehensive clarification on the Discord channel, this function `removes excess tokens from the Well. If someone accidentally sends tokens to the Well instead of swapping, such that the balance of tokens in the Well is greater than the stored reserves, they can extract the excess tokens (the ones they accidentally sent to the Well) via the skim() function.`

Business logic of this feature should be, however, considered as flawed. Everyone can call `skim` function - thus there is no way to guarantee that the legitimate user, who accidentally sent tokens to the Well would be the one who'd have been receiving them. Attacker can either front-run `skim` function or call it before even the legitimate user would notice his/her mistake. Since this basically implies loss of funds (a legitimate user won't be able to receive his/her excess tokens - as those funds would have been stolen by the attacker) - this issue has been estimated as High.

The current implementation allows the attacker to either front-run `skim` function or call it even before the legitimate user notices that excess tokens belong to him/her.

## Proof of Concept

There are two attack scenarios which allows malicious actor to steal other users funds:

### (1) Front-run attack on `skim` function

Attacker monitors mempool's transaction for `skim` operation. If he notices that someone called `skim` - then he front-runs it, by providing `skim` with his own address. The excess token will be transferred to the attacker instead.

### (2) Calling `skim` before legitimate user

Attacker observing a blockchain transaction and when he spots some operations that may suggest that `_tokens[i].balanceOf(address(this)) > reserves[i]`, then he would call `skim` function for his own address even before the legitimate user noticed that it should be him/her who should call this function. In this scenario, attacker calls `skim` way before legitimate user.


## Tools Used

Manual code review

## Recommended Mitigation Steps

Unfortunately, there's no way to implement the logic of this function, unless centralizing some of the operations. Each Well should define one address (e.g. Well creator) with higher privileges. Only that address should be able to redistribute `excess tokens held by the Well`. It could be easily done by observing who sent the excess and then resend the proper amount to the legitimate user. 


## Assessed type

Other