---
name: cython-so-reconstruction
description: Use when reversing a Cython-compiled .so (string tables, LZSS blobs) to Python source.
---

# Cython .so Reconstruction

Use when reversing a Cython-compiled Python module (.so, ARM/x86 ELF) back to source-level Python. Companion to `reverse-engineer-anything`. Decodes the InitConstants blob exactly, so every string constant is recovered rather than guessed.

## Identify the module
- `nm`/`.symtab` for `__Pyx_*` symbols: `__pyx_pf_4<mod>_<func>`, `__pyx_pw_4<mod>_<func>`, `__Pyx_CreateCodeObjects`, `__Pyx_InitConstants` => Cython build.
- **Decode the symbol mangling before disassembling anything.** Cython encodes
  `<len><name>` runs in the symbol, so `__pyx_pf_15cython_testing_9pure_mode_3foo`
  is module `cython_testing`, class `pure_mode`, method `foo`. Segment count is a
  structural signal: 2 segments = module-level function, 3 segments = method.
  This gives you the exact module/class/method tree for free — run
  `scripts/decode_cython_symbols.py` over `nm` output instead of reading mangled
  names by eye. `nm -S` on the same pass gives `st_size` for function bounds.
- `strings` reveals the Cython version (e.g. `Cython 3.3.0`) and the original
  `.py` filename. **The version decides the string-table format** — see the
  LZSS section below.

## Decode the string-constant table (the high-value step)
Cython 3.x stores interned strings in a `__Pyx_InitConstants.bytes` blob plus a length table; decoding both recovers EVERY string constant exactly.
1. Find the blob address from the symbol table; find the interpreter loop by scanning `.text` for the `adr`/`adrp`+`add` pair computing the blob address (xref scan with capstone, not objdump on cross-arch).
2. The loop signature: `ldrb w8, [x25], #4` (post-index, stride 4) then an `and` with an immediate (the length mask) then a create-string call with `x0 = blob + offset`. The table is u32 LE lengths, one 4-byte entry per string; strings are concatenated back-to-back after the table.
3. **Read the length mask from the disasm `and` immediate — it is per-module, not fixed.** Observed: `and x19, w8, #0x1f` (5-bit, small module) and `and x19, w8, #0x7ff` (11-bit, large module). A wrong mask truncates or overruns every string.
4. Walk: `off=0; for each u32 len: s = blob[off:off+(len & MASK)]; off += (len & MASK)`. The walk must consume the blob exactly; if it doesn't, the table start, base, or mask is wrong.
5. Slot order == table order. **Derive the slot base from the store instruction in this module, do not assume a fixed offset.** Observed slot bases: `mstate+0xa0` (small module) and `mstate+0x750` (large module). The base is where `str x0, [x8, #off]` lands; slot `i` lives at `base + i*8`.

## Cython 3.x LZSS-compressed string tables
When `strings` reports Cython 3.x (3.0+), the `__Pyx_InitConstants` blob is **not**
raw concatenated text — Cython runs the string table through its own LZSS and
stores it compressed. Tell-tale: the blob at the `cstring` symbol begins with
non-textual bytes and no readable string data, and `__Pyx_InitConstants.cstring`
(plus `__Pyx_DecompressString_LZSS`) appears in the symbol table.

1. Read the Cython version string from the target, then obtain **that exact
   version's** source (`pip download cython==<ver> --no-binary :all:`). The
   authoritative decoder is `__pyx_lzss_decompress` in
   `Cython/Utility/StringTools.c`; `Cython/LZSS.py` carries `WINDOW_SIZE` and
   `MIN_LENGTH`. Port that function — do not invent a variant, and do not assume
   the scheme is stable across Cython majors.
2. Token layout of a back-reference (verified on aarch64 Cython 3.3.0): a 2-byte
   token where the **low byte carries the offset's low 8 bits** and the **high
   byte packs `(offset_high_3_bits << 5) | (match_len - MIN_LENGTH)`**. The mask
   `hi & 0x1F` is the match length. In the flag-byte variant the sentinel is the
   **bit-8 mask on the flag word (`flags & 0x100`)**, not bit 9 — see
   `references/cython-blob-variants.md`. Getting either wrong does **not** fail
   loudly: it returns truncated but plausible-looking output (a few hundred bytes
   of leading whitespace/control characters) that reads as success. Validate by
   exact source-byte consumption before trusting any decode.
3. **Validate the decoder by exact source consumption, not by output length.**
   A correct port consumes all but the last byte of the blob (observed 7602 of
   7603) and the module's init loop compares against a literal of the compressed
   size (`cmp #0x1db2`). Match both numbers before using the decoded buffer; a
   decoder that stops early produces a short buffer that silently truncates every
   later string in the table.
4. **Take the decompressed size from the init function's disassembly, never by
   brute force.** The decompressor is called as
   `__Pyx_DecompressString_LZSS(blob, dst_len)`; the second argument is a literal
   loaded into a register just before the call. Brute-forcing candidate sizes
   wastes turns and still returns `None` when the token layout is wrong.
4. After decompression, the length-table walk in the section above applies to the
   decompressed buffer. Strings were **sorted by `(is_interned, text)` before
   concatenation**, so a concatenated blob with no boundaries is recoverable by
   re-sorting candidate splits — use this to sanity-check the table.

Full comparison of the raw / LZ77-style / LZSS blob layouts, and the
`__Pyx_InitConstants` disasm recipe for recovering `dst_len`: see
`references/cython-blob-variants.md`.

## Resolve the PLT map from the GOT, never from naive offsets
`__pyx_pf_*` functions call through `.plt` stubs. The naive `stub[i] = plt_sh_addr + 16*(i+1)` is **wrong on aarch64: PLT0 is 32 bytes, so every real stub sits at `naive - 16`.** Resolving the naive way mislabels every imported CPython API call and poisons the whole semantic trace.
1. Disassemble `.plt` directly. For each stub, follow its `adrp`+`ldr` pair to a GOT slot address.
2. Map that GOT `r_offset` back through `.rela.plt` (`r_offset` → symbol name via `.dynsym`).
3. Build `{stub_addr: symbol_name}` and use it for every `bl` annotation. Verify sanity on known-good pairs (`PyBytes_FromStringAndSize`, `memcpy`, `PyUnicode_DecodeUTF8`, `PyFloat_FromDouble`) before trusting the trace.

## Attribute strings to functions
Scan all of `.text` for `ldr xN, [xM, #off]` where `off` falls in the slot range, and map each hit to the containing `__pyx_*` symbol. This yields per-function constant usage, which pins down each function's logic (imports, subprocess args, exception types, printed messages).

### Register tracking rules (this is where naive scripts break)
- Track `adrp xN, #page` then `add xN, xN, #imm` into a concrete address; only then can a following `ldr xM, [xN, #off]` be tested against the slot range.
- **Build the tracker as a per-instruction snapshot list, never one final dict.**
  A single-pass dict returns only the register state at function end, so every
  earlier `ldr` resolves against registers that a later instruction overwrote.
  The symptom is silent: string-slot hits drop to zero even though the addresses
  are all present. Return `vals[i]` = state *before* `ins[i]` and index it.
- **Propagate the destination of `ldr xD, [xB, #off]` when `xB` holds a known struct base.**
  Cython reaches its interned strings through a global struct pointer
  (`adrp xB,P; add xB,xB,#o; ldr xD,[xB,#k]`), so `xD` legitimately carries the
  derived slot address. Poisoning `ldr` destinations here is what makes string
  references vanish. The safety net is the exact-match test against the slot
  range: a propagated address that misses the range is discarded, so no false
  reference is invented.
- Poison the destination of any *other* `ldr`/`ldp`/`stp`/`add`/`orr`/`mov`-with-imm/`blr`
  result — those hold values or pointers, not slot addresses. A stale value is
  worse than a missing one.
- **`ins.op_str` does not include the mnemonic.** Write operand regexes against
  `op_str` alone (`^([xw]\d+), \[([xw]\d+)(?:, #(0x[0-9a-f]+))?\]$`); a pattern
  that assumes the mnemonic is present matches nothing and looks like "no hits".
- Reuse one snapshot list for both the string-slot scan and the call trace —
  recomputing it per pass doubles the cost on large modules.
- Xref-scanning `.text` for the raw blob address frequently returns **0 hits** (aarch64 addressing is page-relative). When that happens, do not conclude the blob is unused — go through `__Pyx_InitCachedConstants` / `__Pyx_CreateCodeObjects` instead and recover `co_consts` tuples by tracking which slot index each `ldr` pulls from.

### Parsing capstone text output
Do **not** `split(',')` on `ins.op_str`: memory operands and shift expressions contain commas inside brackets, which corrupts the token. Match operands with a regex such as `MEM = re.compile(r'\[(x\d+)(?:, #(0x[0-9a-f]+))?\]')`. For `add`, parse the destination with `DST = re.compile(r'^([xw]\d+),')` and only `int()` the immediate after stripping the `0x` — a register token like `x21` will otherwise raise.

## Get the module structure
Disassemble `__pyx_pymod_exec_<mod>` (the module-level body) and annotate it the same way. That single region yields the **exact import list and import order**, which is the skeleton the reconstructed source needs.

Scan `.rodata` for qualnames before disassembling: `<module>.<Class>` /
`<module>.<func>` C strings give the class-and-method tree directly, including
methods whose `__pyx_pf_*` symbols are missing. A qualname whose second segment
starts uppercase is a class member. This is cheaper than walking
`__Pyx_Py3ClassCreate` and covers the gaps in the symbol table.

## Parse PyMethodDef as 32 bytes
`struct '<QQII'` (name ptr, C fn ptr, flags, doc), **not** `<QQQQ` — the
24-byte layout misreads every entry after the first. Use `nm -S` for `st_size`,
then `n = st_size // 32`.

## Noise filter for semantic flow
When reducing a per-function trace to semantic flow, drop the Cython/CPython plumbing so the real logic stands out: `_Py_Dealloc`, `memset`, `PyUnicode_FromOrdinal`, `PyUnicode_New`, `PyNumber_Long`, `PyObject_Size`, `PyErr_*`, `PyThreadState_*`, `__Pyx_AddTraceback`, `Py_XDECREF`, `RecursiveCall`, `GetIter`/`Iternext`.

## Function bounds
Take sizes from `nm -S` (`.symtab` has `st_size`); do not infer a function's end from the next symbol's start — Cython pads and emits multiple sub-objects per function.

## Pitfalls
- A naive byte-scan for `0xd8`/`0xd0` opcode bytes desyncs (operands get read as opcodes). Walk the stream with a real length table per opcode, or skip stream-walking entirely and use the length-table method above.
- **Diff the module list against `find <repo> -name '*.so'` before running a batch generator.**
  A module missing from the list is silent — no error, no empty output, just one
  fewer file. Verify the generated file count equals the on-disk `.so` count.
- **Verify emitted lines with the right grep.** Generator output is indented
  inside function bodies, so `grep '^S_'` returns 0 and reads as total failure
  when the reconstruction is complete. Grep `S_[0-9a-f]* =` (no anchor).
- **Sanitize generated identifiers.** A Cython method can be named `lambda`,
  `None`, or a digit-leading name; emitting it raw produces a `SyntaxError` in
  the generated file. Suffix Python keywords and reserved constants with `_`,
  and prefix a leading digit with `_`.
- **The InitConstants blob is often compressed, and the scheme depends on the Cython version.** Tell-tale: the blob does not begin with readable string data. Cython 3.x uses its own LZSS (recipe in the section above); other builds show `0xff` separator runs with a flag byte per 8 items. Decode **first**, then apply the length-table walk to the decompressed buffer. Schemes and decompressor recipes: `references/cython-blob-variants.md`.
- Never brute-force the LZSS output size. A wrong size returns `None`, identical to a wrong token layout, so brute force cannot distinguish the two failures — read `dst_len` from the disasm instead.
- Masked length bytes mean the raw table bytes, not the decoded lengths, are the source of truth — and the mask itself is module-specific (see step 3 above).
- The first constant may legitimately contain leading whitespace/control bytes (e.g. `" \n\n\n\t[!] Setup failed"`) — that is real source content, not corruption.
- Annotate every recovered constant with the string slot index it came from so later cross-checks (a function using slot 526 = `sys`) stay verifiable.

See `references/cython-blob-variants.md` for the compressed-blob decompressors, the per-module table/slot-base/mask comparison, and the co_consts tuple recovery recipe.

Run `scripts/decode_cython_symbols.py` (accepts a `.so` or `nm` output) to turn
mangled `__pyx_pf_*` / `__pyx_pw_*` names into the module/class/method tree.

Once the string table is recovered and the remaining work is emitting runnable
`.py` modules across a repo, follow `references/generator-and-trace.md`: the
three-stage pipeline, the semantic-trace emission shape, the wrapper-vs-
implementation demangling, and the compile/coverage gate before packaging.

## Reconstruction confidence
- VERIFIED: function names (symbols), all constants, call targets (PLT/dynsym resolution), exception handlers.
- INFERRED: loop/menu bodies not directly visible — reconstruct the most consistent structure from the constants and label it as inferred.
- Capstone on cross-arch: use `capstone.CS_ARCH_AARCH64` (NOT `CS_ARCH_ARM64`) for aarch64 ELFs when objdump lacks support.
