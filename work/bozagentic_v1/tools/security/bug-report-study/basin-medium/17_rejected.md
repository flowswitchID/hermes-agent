# #17: division before multiplication in readLastReserves() of LibLastReserveBytes.sol 
Labels: ['invalid', '2 (Med Risk)', 'withdrawn by warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/libraries/LibLastReserveBytes.sol#L97


# Vulnerability details

## Impact
```
 iByte = (i - 1) / 2 * 32;
```
In line 97 of LibLastReserveBytes.sol, there is a division before multiplication. This can lead to precision/rounding errors 

## Proof of Concept
The logic with the issue is here --> https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/libraries/LibLastReserveBytes.sol#L97  

```
iByte = (i - 1) / 2 * 32;
```

We can make a demo function that outputs the results for when i = 4 and division is done before multiplication and another case when multiplication is done before multiplication (the right way). 

```
    function demo()
        public
        view
        returns ( uint divBeforeMul, uint mulBeforeDiv )
    {
        uint i = 4;

        divBeforeMul =  (i - 1) / 2 * 32;
        mulBeforeDiv =  (i - 1) * 32 / 2;
    }
```

Running this gives `divBeforeMul` as 32 and `mulBeforeDiv` as 48. `divBeforeMul` is 32 because `(4 - 1) / 2 = 1.5` but since solidity uints have no decimal points its reduced to 1. `1 * 32` = 32. 
However doing it the other way (multiplication before division) gives 48. This is because `(4 - 1) * 32 = 96` and  `96 / 2 =  48`. 48 is the more exact or correct value.    

## Tools Used
VS CODE 
## Recommended Mitigation Steps
do the multiplication first 
```
  iByte = (i - 1) * 32 / 2;

```


## Assessed type

Math