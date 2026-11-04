# Cython InitConstants blob variants

Depth for the SKILL.md procedure. Load when a module's string-table walk does not
consume its blob exactly, or when the blob looks binary rather than textual.

## Per-module parameter comparison (observed)

| parameter | small module | large module |
|---|---|---|
| length mask (`and` immediate) | `0x1f` | `0x7ff` |
| slot base | `mstate + 0xa0` | `mstate + 0x750` |
| string count | 52 | 569 |
| blob | raw | **LZ77-compressed** |
| extra layout | none | bytecode blobs sit immediately after the slot array |

**Do not hardcode any of these.** Read the mask from the `and` immediate, the slot
base from the `str` destination, and the count from where the walk stops consuming.

## Compressed blob (LZ77-style)

Tell-tale: blob starts with non-textual bytes and contains `0xff` separator runs.
Decode it **first**, then apply the length-table walk to the decompressed buffer.

Scheme — a flag byte governs the next 8 items, bits consumed low-to-high:
- bit 0 (literal): copy the next byte verbatim.
- bit 1 (back-reference): read the next 1-2 bytes and copy from the already-built
  output window.
  - if `b0 >= 0x80`: 3-byte form, `off = ((b1 & 0x7f) << 7) + (b0 & 0xff)`,
    `len = b2 + 3`.
  - else: 2-byte form, `off = ((b1 & 0x60) << 2) + (b0 & 0xff)`, `len = (b1 & 0x1f) + 3`.
  - else (b0 < 0x80, fallback 2-byte): `off = b0`, `len = b1 + 3`.

A correct decompressor is self-validating: the output size is exactly determined by
the input (no slack, no trailing partial item). Observed 13035 -> 21866 bytes. If the
sizes do not land exactly, a back-reference form is wrong — fix the decoder before
touching the table.

## Bytecode blobs after the slot array

In the compressed layout the slot array is followed immediately by 3-5 bytecode
blobs (the `co_consts` tuples for the module + each function). Their file offsets
are only knowable after decompression; recover them by walking the decompressed
buffer and identifying the boundaries, not by guessing fixed offsets.

Opcode `0xd8` / `0xd0` in those blobs is a **string reference** encoded as
`(offset, length)` — resolve it against the string table rather than decoding it as
data. That is how `co_consts` tuples are mapped back to source constants.

## Recovering `co_consts` tuples

Disassemble `__Pyx_InitCachedConstants`. Each tuple is built with a
`PyTuple_New(n)` followed by n stores from slot-address registers. Track
`adrp`+`add` into concrete addresses, test each against the slot range
(`base <= addr < base + nstr*8`), and record `(tuple_index, slot_index)`. That gives
you `co_consts` exactly, which pins the literal arguments in each function body.

Verify the count against `__Pyx_CreateCodeObjects`: the number of code objects is
`1 (module) + number of top-level functions`.

## Verifying the PLT map before trusting a trace

Sanity-check the resolved `{stub: symbol}` map against at least four known CPython
entry points before annotating anything. If `PyBytes_FromStringAndSize`, `memcpy`,
`PyUnicode_DecodeUTF8`, or `PyFloat_FromDouble` do not resolve to themselves, the
aarch64 `-16` shift (PLT0 = 32 bytes) has not been applied and every `bl`
annotation in the trace is wrong.

## Output shape the operator expects

The final artifact is a runnable `.py` file, not prose. Every recovered constant is
tagged `[VERIFIED]`; reconstructed control flow that is implied by the verified
call order but not directly visible is tagged `[INFERRED]`. Keep both tags in the
delivered source so the operator can see exactly what is byte-exact.
