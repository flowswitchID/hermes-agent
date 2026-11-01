# #40: `MIPS` - `RDHWR`(opcode 0x1F, function code 0x3B) instruction is not handled
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_primary']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/MIPS.sol#L640


# Vulnerability details

## Impact
Incorrect resolution of dispute game - False claims can be resolved as True

## Proof of Concept
Every Go routine(program) starts with a small stack size and whenever more stack is required, there is an action taken to increase the stack size.
This is handled by all syscall wrapper functions have this check at the beginning of the function.

For example, here's how it looks like for `syscall_init`:
```mips
.text:000C8D0C                             .globl syscall_init
.text:000C8D0C             syscall_init:
.text:000C8D0C 8F C1 00 08                 lw      $at, 8($fp)
.text:000C8D10 00 3D 08 2B                 sltu    $at, $sp
.text:000C8D14 14 20 00 06                 bnez    $at, loc_C8D30
.text:000C8D18 00 00 00 00                 nop
.text:000C8D1C 00 1F 18 25                 move    $v1, $ra
.text:000C8D20 0C 02 D6 90                 jal     runtime_morestack_noctxt
.text:000C8D24 00 00 00 00                 nop
.text:000C8D28 10 00 FF F8                 b       syscall_init
.text:000C8D2C 00 00 00 00                 nop
.text:000C8D30              # ---------------------------------------------------------------------------
.text:000C8D30
.text:000C8D30             loc_C8D30:
.text:000C8D30              # Actual logic goes here
                                            ...
```
As shown in the code snippet, if it requires more stack it calls `runtime_morestack` or `runtime_morestack_noctxt` function to increase size of the stack.

And the `runtime_morestack`/`runtime_morestack_noctxt` functions include logic uses `RDHWR` instruction that stands for `Read Hardware Register`, as shown below:
```mips
.text:000B8ACC                             .globl runtime_save_g
.text:000B8ACC             runtime_save_g:
.text:000B8ACC 3C 17 02 1E+                lb      $s7, runtime_iscgo
.text:000B8AD4 12 E0 00 05                 beqz    $s7, locret_B8AEC
.text:000B8AD8 00 00 00 00                 nop
.text:000B8ADC 00 03 B8 25                 move    $s7, $v1
.text:000B8AE0 7C 03 E8 3B                 rdhwr   $v1, $29         # <------ Here
.text:000B8AE4 AC 7E 90 00                 sw      $fp, -0x7000($v1)
.text:000B8AE8 00 17 18 25                 move    $v1, $s7
.text:000B8AEC
.text:000B8AEC             locret_B8AEC:
.text:000B8AEC 03 E0 00 08                 jr      $ra
.text:000B8AF0 00 00 00 00                 nop
.text:000B8AF0              # End of function runtime_save_g
```
Specifically, it is used with first argument as 29, which means to read local user storage data which is stored in hardware register.

Since this instruction is not handled in `MIPS` VM, the step for this instruction can't succeed because it reverts.
As a result, the invalid leaf couldn't be countered which makes it valid.

## Tools Used
Manual Review

## Recommended Mitigation Steps
`RDHWR` instruction has to be handled in `MIPS` VM.



## Assessed type

Context