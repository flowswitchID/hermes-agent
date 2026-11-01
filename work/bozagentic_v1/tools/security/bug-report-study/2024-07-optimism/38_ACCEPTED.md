# #38: `MIPS` - No syscall handling for `mmap2`(4210)
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_04_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/MIPS.sol#L151


# Vulnerability details

## Impact
Incorrect resolution of dispute game - True claim will be resolved as False

## Proof of Concept
In `MIPS` vm, `mmap` syscall is handled by checking syscall no. 4090.
However, `mmap2` syscall(4210) is usually used allocate/map memories.

Here's code snippet of low-level function `syscall_mmap`.
(The assembly below is generated from ELF file built from `op-program-client`)

```mips
.text:000CBAB4                             .globl syscall_mmap
.text:000CBAB4             syscall_mmap:
.text:000CBAB4 8F C1 00 08                 lw      $at, 8($fp)
.text:000CBAB8 00 3D 08 2B                 sltu    $at, $sp
.text:000CBABC 14 20 00 06                 bnez    $at, loc_CBAD8
.text:000CBAC0 00 00 00 00                 nop
.text:000CBAC4 00 1F 18 25                 move    $v1, $ra
.text:000CBAC8 0C 02 D6 90                 jal     runtime_morestack_noctxt
.text:000CBACC 00 00 00 00                 nop
.text:000CBAD0 10 00 FF F8                 b       syscall_mmap
.text:000CBAD4 00 00 00 00                 nop
.text:000CBAD8              # ---------------------------------------------------------------------------
.text:000CBAD8
.text:000CBAD8             loc_CBAD8:
                            .....
                            .....
.text:000CBB50 00 00 00 00                 nop
.text:000CBB54              # ---------------------------------------------------------------------------
.text:000CBB54
.text:000CBB54             loc_CBB54:
.text:000CBB54 8F A1 00 2C                 lw      $at, 0x2C($sp)
.text:000CBB58 AF A1 00 04                 sw      $at, 4($sp)
.text:000CBB5C 8F A1 00 30                 lw      $at, 0x30($sp)
.text:000CBB60 AF A1 00 08                 sw      $at, 8($sp)
.text:000CBB64 8F A1 00 34                 lw      $at, 0x34($sp)
.text:000CBB68 AF A1 00 0C                 sw      $at, 0xC($sp)
.text:000CBB6C 8F A1 00 38                 lw      $at, 0x38($sp)
.text:000CBB70 AF A1 00 10                 sw      $at, 0x10($sp)
.text:000CBB74 8F A1 00 3C                 lw      $at, 0x3C($sp)
.text:000CBB78 AF A1 00 14                 sw      $at, 0x14($sp)
.text:000CBB7C AF A2 00 18                 sw      $v0, 0x18($sp)
.text:000CBB80 0C 03 43 F8                 jal     syscall_mmap2    # <----------- mmap calls mmap2 syscall
.text:000CBB84 00 00 00 00                 nop
.text:000CBB88 8F A1 00 1C                 lw      $at, 0x1C($sp)
.text:000CBB8C 8F A2 00 20                 lw      $v0, 0x20($sp)
.text:000CBB90 8F A3 00 24                 lw      $v1, 0x24($sp)
.text:000CBB94 AF A1 00 48                 sw      $at, 0x48($sp)
.text:000CBB98 AF A2 00 4C                 sw      $v0, 0x4C($sp)
.text:000CBB9C AF A3 00 50                 sw      $v1, 0x50($sp)
.text:000CBBA0 8F BF 00 00                 lw      $ra, 0($sp)
.text:000CBBA4 27 BD 00 28                 addiu   $sp, 0x28
.text:000CBBA8 03 E0 00 08                 jr      $ra
.text:000CBBAC 00 00 00 00                 nop
.text:000CBBAC              # End of function syscall_mmap
```

As shown in `.text:000CBB80`, `mmap` syscall calls `mmap2` syscall.

Here's code snippet of low-level `syscall_mmap2` function.

```mips
.text:000D0FE0                             .globl syscall_mmap2
.text:000D0FE0             syscall_mmap2:                           
.text:000D0FE0 8F C1 00 08                 lw      $at, 8($fp)
.text:000D0FE4 00 3D 08 2B                 sltu    $at, $sp
.text:000D0FE8 14 20 00 06                 bnez    $at, loc_D1004
.text:000D0FEC 00 00 00 00                 nop
.text:000D0FF0 00 1F 18 25                 move    $v1, $ra
.text:000D0FF4 0C 02 D6 90                 jal     runtime_morestack_noctxt
.text:000D0FF8 00 00 00 00                 nop
.text:000D0FFC 10 00 FF F8                 b       syscall_mmap2
.text:000D1000 00 00 00 00                 nop
.text:000D1004              # ---------------------------------------------------------------------------
.text:000D1004
.text:000D1004             loc_D1004:
.text:000D1004 AF BF FF D0                 sw      $ra, -0x30($sp)
.text:000D1008 27 BD FF D0                 addiu   $sp, -0x30
.text:000D100C AF BF 00 00                 sw      $ra, 0($sp)
.text:000D1010 24 01 10 72                 li      $at, 0x1072         # <----------- syscall_no=0x1072
.text:000D1014 AF A1 00 04                 sw      $at, 4($sp)
.text:000D1018 8F A1 00 34                 lw      $at, 0x34($sp)
.text:000D101C AF A1 00 08                 sw      $at, 8($sp)
.text:000D1020 8F A1 00 38                 lw      $at, 0x38($sp)
.text:000D1024 AF A1 00 0C                 sw      $at, 0xC($sp)
.text:000D1028 8F A1 00 3C                 lw      $at, 0x3C($sp)
.text:000D102C AF A1 00 10                 sw      $at, 0x10($sp)
.text:000D1030 8F A1 00 40                 lw      $at, 0x40($sp)
.text:000D1034 AF A1 00 14                 sw      $at, 0x14($sp)
.text:000D1038 8F A1 00 44                 lw      $at, 0x44($sp)
.text:000D103C AF A1 00 18                 sw      $at, 0x18($sp)
.text:000D1040 8F A1 00 48                 lw      $at, 0x48($sp)
.text:000D1044 AF A1 00 1C                 sw      $at, 0x1C($sp)
.text:000D1048 0C 03 45 1A                 jal     syscall_Syscall6     # <---------- Call syscall here
.text:000D104C 00 00 00 00                 nop
.text:000D1050 8F A1 00 20                 lw      $at, 0x20($sp)
.text:000D1054 8F A2 00 28                 lw      $v0, 0x28($sp)
.text:000D1058 10 40 00 2A                 beqz    $v0, loc_D1104
.text:000D105C 00 00 00 00                 nop
.text:000D1060 AF A1 00 2C                 sw      $at, 0x2C($sp)
.text:000D1064 24 03 00 02                 li      $v1, 2
.text:000D1068 00 62 18 2B                 sltu    $v1, $v0
.text:000D106C 14 60 00 0A                 bnez    $v1, loc_D1098
.text:000D1070 00 00 00 00                 nop
.text:000D1074 38 43 00 02                 xori    $v1, $v0, 2
.text:000D1078 14 60 00 19                 bnez    $v1, loc_D10E0
.text:000D107C 00 00 00 00                 nop
.text:000D1080 3C 17 02 19                 lui     $s7, 0x219
.text:000D1084 8E E2 74 08                 lw      $v0, syscall_errENOENT
.text:000D1088 3C 17 02 19                 lui     $s7, 0x219
.text:000D108C 8E E3 74 0C                 lw      $v1, off_219740C
.text:000D1090 10 00 00 1E                 b       loc_D110C
.text:000D1094 00 00 00 00                 nop
                                           .....
```

As shown in the above code snippet, syscall no 0x1072(4210) is used for mmap.
In `MIPS` vm, there's no handling of syscall no 0x1072, thus the post state becomes incorrect which makes true claim to be false at the end.

## Tools Used
Manual Review

## Recommended Mitigation Steps
`mmap2` should also be handled in `MIPS` vm.



## Assessed type

Context