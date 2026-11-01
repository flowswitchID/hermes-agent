# #238: Invariants doesn't checked
Labels: ['bug', '3 (High Risk)', 'disagree with severity', 'primary issue', 'sponsor disputed', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L226-L228
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L436-L439


# Vulnerability details

## Impact

Liquidity providers might lost their funds. Because wellFunction can be arbitrary.

## Proof of Concept

I've asked `publius` about `wellFunction`, and he respond -- that anyone can create any `wellFunction` and pass it to the `Well`.
So, let's consider for example `wellFunction` as `ConstantProduct`, if we call a lot of `swap` function, we got that actual reserves is less than amount of liquidity.
I've created python explanation:
```python

import math


def make_ts(a, b):
    return int(math.sqrt(a * b) * 2)


a = 1_000_000_000
b = 1_000

ts = make_ts(a, b)
print(ts)


def swap(a, b, ts, add=10_000_000, l=True):
    if l:
        a = a + add
        r = ((ts // 2) ** 2)
        r = r // a
        return a, r, b - r, make_ts(a, r)
    b = b + add
    r = ((ts // 2) ** 2)
    r = r // b
    return r, b, a - r, make_ts(r, b)


for i in range(1000):
    res = swap(a, b, ts)
    a, b, _, _ = res
for i in range(1):
    res = swap(a, b, ts)
    print(i, res)
    a, b, _, _ = res

a += 0.1
b += 0.5
print(make_ts(a, b))

if __name__ == "__main__":
    pass
```

result: 

```
2000000
0 (11010000000, 90, 0, 1990879)
1996401
```

After 1_000 swaps we got significant deviations.

This leads:
* Liquidity providers will lost their funds
* Impossibility to add small amount of liquidity 
  * Because this line `lpAmountOut = _calcLpTokenSupply(wellFunction(), reserves) - totalSupply();` will be reverted due to subtraction overflow. So users who want to add a bit of liquidity won't be able to do it.

## Tools Used

Manual review.

## Recommended Mitigation Steps

After trade functions add assertion: `lp(reserves) >= liquidty`. 


## Assessed type

Invalid Validation