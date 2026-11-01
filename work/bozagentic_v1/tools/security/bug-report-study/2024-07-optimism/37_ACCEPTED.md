# #37: `MIPS` - Incorrect handling of memory mapping
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor acknowledged', 'sufficient quality report', 'unsatisfactory', ':robot:_04_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/MIPS.sol#L176-L179


# Vulnerability details

## Impact
Incorrect resolution of dispute game - True root claim is resolved as False

## Proof of Concept
```c
void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset);
```
The above code-snippet shows an interface of low-level `mmap` function.

The first parameter is a preferred addr for mapping the memory, but when it is set to NULL(which is most of the case), the address will be determine in run-time, based on different factors like:

- Gaps in memory, for example, if memories that had been allocated were unmapped using `munmap` and the size of memory to allocate fits in it, it will use this as mapped address.
- If ASLR(Address Space Layout Randomization) flag is setup, there is randomization applied in finding memory gap.

However, in MIPS, it is assumed that newly mapped memory always exists at the last of the heap:
```solidity
if (a0 == 0) {
    v0 = state.heap;
    state.heap += sz;
} else {
    v0 = a0;
}
```

`mmap` does not guarantee that mapped memory exists in heap, it can be anywhere in virtual memory.
Also based on above facts, the resulting `$v0` might have different value between actual run-time and in MIPS, which will result in incorrect game resolution.

## Tools Used
Manual Review

## Recommended Mitigation Steps
Mitigation is not 100% clear because it depends on run-time how memory is managed.


## Assessed type

Context