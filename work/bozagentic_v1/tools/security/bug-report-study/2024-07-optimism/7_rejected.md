# #7: MIPS: The `rtReg` will be incorrectly overwritten for store instructions (`opcode >= 0x28`)
Labels: ['invalid', '3 (High Risk)', 'withdrawn by warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/main/packages/contracts-bedrock/src/cannon/MIPS.sol#L733-L739


# Vulnerability details

For `opcode >= 0x28` (store instructions), the `rt` register should not be overwritten, instead this is the register where the data is copied from to memory by the store instructions.

However, in the code below, the register that is written to `rdReg` will be assigned to `rtReg` for store instructions (`opcode >= 0x28`)

[MIPS.sol#L733-L739](https://github.com/code-423n4/2024-07-optimism/blob/main/packages/contracts-bedrock/src/cannon/MIPS.sol#L733-L739)
```solidity
            } else if (opcode >= 0x28 || opcode == 0x22 || opcode == 0x26) {
                // store rt value with store
                rt = state.registers[rtReg];

                // store actual rt with lwl and lwr
                rdReg = rtReg;
            }
```

This means at the very end of the execution the `rtReg` is going to get overwritten, with `val`:

[MIPS.sol#L804](https://github.com/code-423n4/2024-07-optimism/blob/main/packages/contracts-bedrock/src/cannon/MIPS.sol#L804)
```solidity
            // write back the value to destination register
            return handleRd(rdReg, val, true);
```

Here, the `val` can be different from the original value stored in the `rt` register because it can be the combination of the bytes stored in memory and the bytes stored in `rt`. For instance, consider the `sb` instruction:

[MIPS.sol#L1018-L1023](https://github.com/code-423n4/2024-07-optimism/blob/main/packages/contracts-bedrock/src/cannon/MIPS.sol#L1018-L1023)
```solidity
                //  sb
                else if (opcode == 0x28) {
                    uint32 val = (rt & 0xFF) << (24 - (rs & 3) * 8);
                    uint32 mask = 0xFFFFFFFF ^ uint32(0xFF << (24 - (rs & 3) * 8));
                    return (mem & mask) | val;
                }
```

A high-level of what the above instruction is doing is it is taking the upper 24 bits stored in the memory address pointed to by `rs` and the lower 8 bits stored in the `rt` register, then concatenates it to produce the 32-bit `val` which is going to be stored in the memory address pointed to by `rs`. However, it's also going to be incorrectly stored in the `rt` register

So in the end, the `sb` instructions will have an unintended side effect of overwriting the first 24 bits of the `rt` register (also applies to the other store instructions) which is going to lead to unintended consequences.
## Impact

If the L2 STF when translated to MIPS consists of store instructions, this will lead to very egregious errors where the register pointed to by `rt` will become corrupted when it should not, leading to unintended consequences (such as leading to a correct output root not being able to be confirmed because the MIPS program will report an invalid VM status)

## Tools Used

Manual Review

## Recommended Mitigation Steps

Zero the `rdReg` for `opcode >= 0x28`








## Assessed type

Other