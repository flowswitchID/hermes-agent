# #65: the function `swapTo` did not work as expected 
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L264-L290
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L296-L306


# Vulnerability details

## Impact

the function `swapTo` should allow user to swap from token B to token A or `toToken --> fromToken` but this function did not contain the logic to allow the users to make this swap and the function will give the user the toToken rather than the fromToken, same as the `swapFrom` function. more details in POC

before we go to details i talked to the team to make sure this function should allow users to make swap like this `B(DAI) --> A(ETH)`

the conversation between me and the team are below :
``
0xkazim(me)
//Q
and another question please.

in function swapTo this functon allow us to swap tokenTo to get tokenFrom right ? for example:
function swapTo(
// we swap or we give the protocol the toToken(usdc) to get fromToken(ETH)
IERC20 fromToken, // eth
IERC20 toToken, // USDC
uint256 maxAmountIn, // max amount in to avoid slippage
uint256 amountOut, // the amount of eth that transfer out of the protocol and send to the caller
address recipient,
uint256 deadline
)

is that true in the function above or i understand this function incorrectly?

thanks

Brean — 07/05/2023 4:01 PM (the basin team)

//Answer
yes.
``

## Proof of Concept

the function `swapTo` allow the users to swap from `to` token to `from token` but the function did not work like this, imagine a user want to swap from B-->A or from DAI-->WETH the function logic won't allow this swap to happen, all details are in the function below as comments(I write it like this so the reader/judges can understand it much more better)

```solidity

function swapTo(

        IERC20 fromToken, // set to Weth
        IERC20 toToken, // set to DAI
        uint256 maxAmountIn,
        uint256 amountOut, // DAI amount we should get form the swap (out of reserve[DAI])
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256 amountIn) {
        // swap from B(DAI) --> A(Weth)
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = _updatePumps(_tokens.length);
        //get the reserve for both [WETH]= i AND [DAI] = j
        (uint256 i, uint256 j) = _getIJ(_tokens, fromToken, toToken);
        //@audit here we reduce the DAI reserve, this should be increase because we give the protocol DAI to get ETH or in another meaning
        // GIVE DAI TO THE LP AND REDUCE ETH IN THE LP (SWAP B --> A)
        reserves[j] -= amountOut;
        //calculate ETH reserves.
        uint256 reserveIBefore = reserves[i];
        reserves[i] = _calcReserve(wellFunction(), reserves, i, totalSupply());

        // Note: The rounding approach of the Well function determines whether
        // slippage from imprecision goes to the Well or to the User.

        //@audit we set amountIn to be equal to ETH reserve before and after the swap
        amountIn = reserves[i] - reserveIBefore;

        if (amountIn > maxAmountIn) {
            revert SlippageIn(amountIn, maxAmountIn);
        }
        //@audit here we call the function _swapTo, the problem is
        //in this function which it send eth to this address and give us the dai token again !!(this is not swap DAI --> ETH)
        _swapTo(fromToken, toToken, amountIn, amountOut, recipient);
        _setReserves(_tokens, reserves);
    }
```

recognize the comments line we mention(@audit) and it explain that if users want to swap between DAI --> wETH for example the function won't do this and it decrease the reserve of DAI in first(@audit) mention which it should be increased and then the function set the amountIn to be equal to reserve[i] which is Weth token reserve and then send this amount to the address(this) and it send the dai to the users. this is not the swap between B--A but its swap between A-->B

the user will set the function like this

```solidity
function swapTo(

        IERC20 fromToken, // == Weth
        IERC20 toToken, // == DAI
        uint256 maxAmountIn,
        uint256 amountOut, // DAI amount we should get form the swap (out of reserve[DAI])
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256 amountIn) {
        //note make swap that we give DAI and we should get Weth !

        // the function will set (i) as fromToken(WETH) and (j) as toToken(DAI)
          (uint256 i, uint256 j) = _getIJ(_tokens, fromToken, toToken)

          //then decrease the toToken(DAI or j) reserve ! we give DAI to this protocol so why we decrease this !
           reserves[j] -= amountOut

           // then set the amount that it will be send to the address(this)
           // this would be WETH but why WETH reserve increase(send to this address) while we but wETH and we give DAI to this contract!!
           amountIn = reserves[i] - reserveIBefore
            //then this function is called which continue the problem
           _swapTo(fromToken, toToken, amountIn, amountOut, recipient)

    }
```

as we explain above how this is not the logic for the swa between B --> A token now we can check the `_swapTo` to make sure that this function will send us DAI and send WETH to the Well contract.

```solidity
 function _swapTo(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 amountOut,
        address recipient
    ) internal {
        //@audit we send amountIN which is WETH to this contract and then send the DAI to our account(this is not swap from to -->from token !)
        //amountIn = reserve[i] - reserveIBefore which is WETH
        fromToken.safeTransferFrom(msg.sender, address(this), amountIn); // send i(eth) to the contract
        //amountOut = DAI which is not what we should get !
        toToken.safeTransfer(recipient, amountOut);
        emit Swap(fromToken, toToken, amountIn, amountOut, recipient);
    }
```

it's clear how this incorrect logic applied here, for simplest this:
1-we give `DAI` to get `WETH`

2- but we send the `address(this)` the WETH that is calculated in `swapTo` and we send `DAI` that we set as amount out in `swapTO` to the `recipient`

at the end this is not swap from `toToken` to `fromToken`

## Tools Used

manual review

## Recommended Mitigation Steps

recommend to change simple thing in this logic, only move the [j] and [i] may set the correct logic for that:
if we change this line `(uint256 i, uint256 j) = _getIJ(_tokens, fromToken, toToken)` to this:

```solidity
(uint256 i, uint256 j) = _getIJ(_tokens, toToken, fromToken)
```

then all logic will be correct in these lines below:

```solidity
//reserve[j] is weth reserve now
//decrease the WETH because we buy WETH and sell DAI(INCREASE DAI AND DECREASE WETH)
 reserves[j] -= amountOut;

// calculate the DAI before and after swap
 amountIn = reserves[i] - reserveIBefore


 function _swapTo:
        //transfer DAI to address(this) and send the WETH to the recipient address
        fromToken.safeTransferFrom(msg.sender, address(this), amountIn); // send i(eth) to the contract
        toToken.safeTransfer(recipient, amountOut);
```
this could work fine and the logic will be swap from `B` to `A` correctly


## Assessed type

Other