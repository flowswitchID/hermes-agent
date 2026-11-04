# Reconstruction generator and semantic trace

Depth for the SKILL.md procedure. Load when the string table is already recovered
and the remaining work is emitting runnable `.py` modules across a whole repo.

## Pipeline order

1. `lzss.py` — port `__pyx_lzss_decompress` from the target's exact Cython version.
2. `sorev.py` — class `SoRev`: detect `total` (uncompressed size), the length
   table address, the mask, the slot base and slot offset, then split the
   decompressed blob into the string table.
3. `gen.py` — per module: emit constants, then structure, then function bodies
   as a semantic trace. Batch over every `.so`.

Keep the three stages separate. Coupling the decoder to the emitter means a mask
fix forces a full re-run of string extraction for every module.

## Detecting the length table without brute force

The table lives in `.rodata` and is walked by the module-init function. Signature
on aarch64: an `adr xN, TABLE` followed by a length load with post-increment
(`ldrh wD, [rg], #4`) or register-offset (`ldrh wD, [rg, xK, lsl #2]`). Accept
`ldrh`, `ldr`, `ldrb` and `ldrsw` — which one a module uses is compiler-dependent.

- The mask is the first `and xD, xS, #imm` after the `adr`. Fall back from the
  load mnemonic when no `and` is present (`ldrb` -> 0xff, `ldrh` -> 0xffff).
- The entry count `n` comes from a `cmp xZ, #N` before the backward branch.
  Widen the branch-target window to `x.address + 0x18` and the `cmp` lookback to
  5 instructions — narrow windows silently miss the bound.
- Resolve the base with a value-tracking pass (`adrp` + `add xD, xS, #imm`);
  aarch64 addresses are page-relative, so a raw address scan returns nothing.

## Total uncompressed length

Fast path: the module-init function loads the literal destination size into a
register just before the decompress call — on aarch64 it appears as
`mov w1, #0x34f`. Read it, do not search. Fall back to binary search over
`dst_len` only when no immediate is found, and cap the range at
`compressed_len * 40`.

A wrong `dst_len` and a wrong token layout both return `None`, so a failed
decompress cannot distinguish them — fix the decoder before searching sizes.

## Emitted trace shape

```python
def _melogo(*args, **kwargs):
    """__pyx_pw_4logo_1_melogo  @ 0x88e0 size=3804  [951 insns]"""
    call_8974 = FASTCALL_D()   # __Pyx_PyObject_FastCallDict
    S_5128 = '\n'
    call_8e04 = JOIN()   # __Pyx_PyUnicode_Join
```

- One `S_<addr> = <repr>` per resolved string-slot load, at the load site.
- One `call_<addr> = <TAG>()` per `bl` into a CPython or `__Pyx_*` helper, with
  the raw symbol as a trailing comment. Map helper -> tag through a CALLMAP
  table so the same helper renders consistently across modules.
- Drop control-flow markers (`b.cond`, `cbz`, `cbnz`) — they add noise without
  information. Keep unconditional `b` and `ret`.
- Clear the string-argument register set after each `bl`; Cython reuses argument
  registers, and carrying them forward produces phantom arguments on later calls.

## Demangling wrapper vs. implementation symbols

- `__pyx_pw_<len><mod>_<len><rest>` is the argument-parsing wrapper.
- `__pyx_pf_<len><mod>_<len><rest>` is the implementation.

Emit the wrapper name; it is the Python-visible entry point. Demangle with
`^__pyx_p[fw]_(\d+)([A-Za-z_]\w*?)_(\d+)(.*)$` — the leading integer is a length
prefix, so `__pyx_pw_9useragent_11local` is module `useragent`, name `local`.
The non-greedy module group is what keeps a module name containing underscores
from swallowing the rest.

## Verification gate

Run `python3 -m py_compile` on every generated file and report a per-module line
count and string count. A module that fails to compile is a hard stop — fix the
emitter, do not ship it.

Report the summary as a table the operator can scan at a glance
(`module | lines | strings | status`), then package with a README that states the
recovery method and, explicitly, that function bodies are a semantic trace rather
than statement-level translation. The `.pyx` sources are not in the repo, so the
trace is the ceiling — say so in the artifact, not after delivery.

## Deliverable

The artifact is the archive, not a description of it. Package the generated tree
with `shutil.make_archive` (no `zip` binary on most minimal hosts), include the
README, and send the file. `__pycache__` must be excluded from the archive.
