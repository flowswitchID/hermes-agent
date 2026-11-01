# #45:  Lack of Validation in Aquifer Contract's boreWell Function for Implementation Address
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Aquifer.sol#L34-L64


# Vulnerability details

## Impact
This vulnerability could allow an attacker to deploy a malicious Well that could steal funds or otherwise harm users.

## Proof of Concept
The `boreWell` function in the Aquifer contract allows anyone to deploy a new Well by cloning a pre-deployed Well implementation. The function takes in an implementation address as a parameter, which is the address of the Well implementation that will be used to deploy the new Well. However, the `boreWell` function does not check if the implementation address is valid or if it is a pre-deployed one. This means that an attacker could provide a fake implementation address which could then be used to deploy a malicious Well.
For example, an attacker could create a contract that looks like a Well implementation but that actually contains malicious code. They could then provide the address of this contract to the `boreWell` function. The Aquifer contract would then deploy the malicious contract which could then be used to steal funds or otherwise harm users.
The severity of this vulnerability is increased by the fact that the Aquifer contract is a permissionless contract. This means that anyone can deploy a new Well, which makes it more likely that an attacker will be able to deploy a malicious Well.

## Tools Used
Manual analysis

## Recommended Mitigation Steps
To mitigate this vulnerability, the `boreWell` function should be modified to check if the implementation address is valid. This could be done by checking if the contract at the specified address has the `IAquiferWell` interface implemented.
The function should check if the implementation address is a pre-deployed one


## Assessed type

Access Control