# #217: Predictability of cloned address may be susceptible to frontrunning
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'satisfactory', 'duplicate-181']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L46-L51


# Vulnerability details

## Impact

DoS for the Aquifer.boreWell() function due to frontrunning. 

## Proof of Concept

From the video documentation, Anyone can call `boreWell()` in Aquifer.sol after confirming an implementation contract. The address of the new Well depends solely upon the _salt parameter provided by the user. Once the user's create transaction is broadcasted, the _salt parameter can be viewed by anyone watching the public mempool.

As a result, if a user intends to permissionlessly create a well, his create transaction can be forcefully reverted by an attacker by deploying a well for himself using the user's salt. Here is how this can happen:

- The user broadcasts the create well txn with salt XXX.
- The attacker frontruns the user's txn and creates a well for himself using the same XXX salt.
- The user's original create txn gets reverted as attacker's well already exist on the predetermined address.
- This attack can be repeated again and again resulting in DoS for the Aquifer.boreWell() function.


```
        } else {
            if (salt != bytes32(0)) {
@>              well = implementation.cloneDeterministic(salt);
            } else {
                well = implementation.clone();
            }
```


## Tools Used

VSCode

## Recommended Mitigation Steps

Consider making the upcoming well address user specific by combining the salt value with user's address.

```
        } else {
            if (salt != bytes32(0)) {
+               well = implementation.cloneDeterministic(msg.sender, salt);
            } else {
                well = implementation.clone();
            }
```


## Assessed type

Other