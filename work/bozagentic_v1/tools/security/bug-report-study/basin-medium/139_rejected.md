# #139: Fee-on-transfer 
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L431


# Vulnerability details


## Fee-on-transfer
- Severity: Medium

### Description
Contracts may be vulnerable to errors due to fee-on-transfer tokens. Specifically, some functions transfer tokens without confirming that the actual received amount aligns with the originally intended transfer amount. A discrepancy may occur if the token has a transfer fee, resulting in the final balance being less than anticipated. Moreover, an attacker could potentially exploit latent funds for an unwarranted credit. To prevent these issues, balances should be accurately tracked before and after transfers, using the difference in balance as the actual transferred amount instead of the initial intended amount. 

Example: If a contract sends 10 tokens, but a 1% fee is applied on transfer, the recipient only receives 9.9 tokens. If the contract does not account for this fee, it may inaccurately record that 10 tokens were sent, leading to accounting discrepancies.

NOTE: This detector conducts a recursive check to confirm that 'balanceOf' is properly checked both before and after any token transfer operations, to guarantee accurate accounting.

<details>

<summary>
There are 3 instances of this issue:

</summary>

###
- <br><br>
***File: src/Well.sol
```
 
Line: 431          _tokens[i].safeTransferFrom(msg.sender, address(this), tokenAmountsIn[i])
```
No balance check detected before the transfer. The specified transfer amount: `tokenAmountsIn[i]` might be inaccurate due to possible fee-on-transfer accounting discrepancies. <br><br>use here ->   File: src/Well.sol
```
 
Line: 432          reserves[i] = reserves[i] + tokenAmountsIn[i]
```

[https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L431](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L431)


- <br><br>
***File: src/Well.sol
```
 
Line: 477          _tokens[i].safeTransfer(recipient, tokenAmountsOut[i])
```
No balance check detected before the transfer. The specified transfer amount: `tokenAmountsOut[i]` might be inaccurate due to possible fee-on-transfer accounting discrepancies. <br><br>use here ->   File: src/Well.sol
```
 
Line: 478          reserves[i] = reserves[i] - tokenAmountsOut[i]
```

[https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L477](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L477)


- <br><br>
***File: src/Well.sol
```
 
Line: 558          _tokens[i].safeTransfer(recipient, tokenAmountsOut[i])
```
No balance check detected before the transfer. The specified transfer amount: `tokenAmountsOut[i]` might be inaccurate due to possible fee-on-transfer accounting discrepancies. <br><br>use here ->   File: src/Well.sol
```
 
Line: 559          reserves[i] = reserves[i] - tokenAmountsOut[i]
```

[https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L558](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L558)


</details>

# 


## Assessed type

Token-Transfer