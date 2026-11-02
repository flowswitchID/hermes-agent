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
- **Detect a free-threaded build before hunting string tables.** CPython 3.13t/3.14
  free-threaded modules read the per-thread module state out of the TLS register:
  `mrs xN, tpidr_el0; ldr xN, [xN]`, or via a GOT slot `adrp xN,<page>; add xN,#imm`
  into `__pyx_mstate_global`, then reach every constant as `ldr xM, [xN, #off]`. On
  these builds the interned-string slots are **runtime-filled** with no static reloc
  or string-tab backing — see the free-threaded subsection under the mstate fallback
  and `references/free-threaded-cython.md`.
- `nm -S` also emits `__pyx_pf_<mod>__defaults__` / `__pyx_pw_<mod>__defaults__`
  when a function has default parameter values. Disassemble that stub: its
  stringtab loads are exactly the non-`None` defaults, and it names which function
  carries them. A single default load does **not** mean a single default in the
  tuple — see the signature-validity pitfall below.

## Decode the string-constant table (the high-value step)
Cython 3.x stores interned strings in a `__Pyx_InitConstants.bytes` blob plus a length table; decoding both recovers EVERY string constant exactly.
1. Find the blob address from the symbol table; find the interpreter loop by scanning `.text` for the `adr`/`adrp`+`add` pair computing the blob address (xref scan with capstone, not objdump on cross-arch).
2. The loop signature: `ldrb w8, [x25], #4` (post-index, stride 4) then an `and` with an immediate (the length mask) then a create-string call with `x0 = blob + offset`. The table is u32 LE lengths, one 4-byte entry per string; strings are concatenated back-to-back after the table.
3. **Read the length mask from the disasm `and` immediate — it is per-module, not fixed.** Observed: `and x19, w8, #0x1f` (5-bit, small module) and `and x19, w8, #0x7ff` (11-bit, large module). A wrong mask truncates or overruns every string.
4. Walk: `off=0; for each u32 len: s = blob[off:off+(len & MASK)]; off += (len & MASK)`. The walk must consume the blob exactly; if it doesn't, the table start, base, or mask is wrong.
5. Slot order == table order. **Derive the slot base from the store instruction in this module, do not assume a fixed offset.** Observed slot bases: `mstate+0xa0` (small module) and `mstate+0x750` (large module). The base is where `str x0, [x8, #off]` lands; slot `i` lives at `base + i*8`.
6. **Convert the read-side `ldr` offset through `mstate`, never through the `adrp` page.** objdump annotates the page line with the real offset from the module-state struct (`adrp x25, 63000 <__pyx_mstate+0x408>`), so `mstate = adrp_page - 0x408`. Slot index is then `(adrp_page + ldr_off - mstate - slot_base) // 8`, and **the formula differs per page** — a page reached through an `add xN, xN, #imm` correction has its own base. Assuming `slot_base = page + k` uniformly silently shifts every index on the uncorrected pages. Verify the mapping on two or three known anchor strings (a token regex, an endpoint URL) before trusting the table.

### When the string decode comes up empty (mstate-loaded constants)
Some Cython 3.x builds load interned strings through the module-state struct
(mstate) instead of an `adrp`+`add` to the raw char*, so the `__pyx_string_tab`
walk and the disasm string map both return **nothing**. Do not conclude the
module has no strings — fall back to the raw section (this is the step *after*
the `__Pyx_InitCachedConstants` / `__Pyx_CreateCodeObjects` route also yields
nothing):
1. Extract printable ASCII runs (`[\x20-\x7e]{3,}`) directly from `.rodata` (sweep
   `.data.rel.ro` / `.data` too). These runs ARE the app literals.
2. The runs are fragmented by **ANSI colour escapes** (`\x1b[1;92m`) and separator
   bytes (`0xff`), so one logical string shows up as several short runs
   (`Cho` + `ice ~>>`). Rebuild full strings by joining runs whose gap is a short
   ANSI/control sequence, and read the colours inline to reproduce coloured
   menu/output literals exactly.
3. Forensically confirm a fragment before trusting it: `grep -aob <token>` for the
   file offset, then hexdump ±24 bytes to see whether it is a real literal or a
   coincidental code byte.

### Free-threaded CPython (3.13t / 3.14) — runtime-filled slots, no static decode
When the module is free-threaded, interned-string and constant slots live in the
per-thread mstate and are **zero-initialized at compile time, filled at import**, so
they carry **no `R_AARCH64_RELATIVE` reloc and no `__pyx_string_tab` entry**. Confirmed
on an aarch64 Cython 3.3.0 / CPython 3.14 module: a 40-byte `{slot_ptr,char_ptr,len}`
structural scan returns **0 records**, and reloc-offset extraction over the slot region
returns **0 pairs** — that means *runtime fill*, not a missing table. Do not keep
re-running the same static walk expecting a different answer.
- **Recover the func/method names deterministically via relocs** (no emulation):
  `R_AARCH64_RELATIVE` (type 1027) relocs whose **offset** sits in the writable
  name-table region resolve, via their **addend**, to the `.rodata` c-strings that are
  the `func_name`/`qualname` literals (`clear`, `XDMSX.check`, ...). Sweep
  `{off: cstr(addend)}` over that region — this is the class/method inventory even when
  LTO stripped `.symtab`.
- **The string DATA lives in the `__Pyx_InitConstants.cstring` OBJECT symbol**
  (`readelf -sW` shows it with its `st_size`); the char-pointer table points into it.
  Dump `[st_value, st_value+st_size)` for the full literal pool (ANSI/`0xff`-fragmented
  — join runs split on `\x1b`).
- **Do not fabricate per-slot text bindings or statement-level control flow here.** A
  byte-exact slot->string map needs import-time emulation of the init routine. Bind a
  slot's text only where the instruction pattern plus the literal pool make it
  unambiguous (`GetModuleGlobalName -> GetAttr("system") -> Call` with `"clear"` in the
  pool => `os.system("clear")`); otherwise ship the grounded extraction (names, literal
  pool, endpoints/regexes/UAs, per-function C-API operation traces) and state that
  verbatim source is not recoverable without init-emulation. A plausible-looking
  reconstruction presented as "the decode" is the failure mode — Cython->ARM64 is
  one-way.

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

## Recover bytes constants (`B_xxx`) separately from the string table
The unicode string tab does not carry `bytes` literals. Cython builds them inside
`__pyx_pymod_exec_<mod>` with `PyBytes_FromStringAndSize`, so recover them from
that region:

- Filter the module-exec disassembly to `bl <PyBytes_FromStringAndSize@plt>`.
- The source pointer is the `adrp x0, <page>` + `add x0, x0, #imm` pair in the
  instructions immediately before the call; the length is the `mov w2, #imm`.
- Slice the ELF at that address for that length — that is the exact literal.
- Some calls legitimately pass `xzr`/`#0` (the empty-literal case). Scan the
  whole module-exec range rather than one window: the calls are spread across it,
  and a partial scan reads as "only 3 constants exist".

A recovered `bytes` literal is usually a request-body template, an XOR key, or a
marshalled code object. Port it verbatim — never reconstruct it from the
surrounding unicode strings, which are the *names* the bytes are used with, not
the bytes themselves.

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
- **Invalidate a page-base register the moment any non-`adrp`/`add` instruction
  writes it.** A `ldr x8, [x0, #8]` that loads a Python object pointer into a
  register still holding a page base leaves the tracker believing `x8` is that
  page; the very next `ldr x8, [x8, #0x90]` is then annotated as a stringtab load
  when it is really a `PyTypeObject` slot access (`tp_getattro` sits at offset
  0x90). Exempt control-flow, compare/branch and store instructions; every other
  writer must pop the register before annotation. The tell-tale of a missed
  invalidation is the *same* slot string appearing under four unrelated functions.
- **Two consecutive loads of the SAME stringtab slot are one call, not two.**
  Cython's vectorcall passes the attribute name and the method name as adjacent
  slot loads at one call site. Deduplicate adjacent identical slot references
  per call site before counting constants, or the per-function tally
  double-counts and the reconstructed body gains a phantom second string.
- Poison the destination of any *other* `ldr`/`ldp`/`stp`/`add`/`orr`/`mov`-with-imm/`blr`
  result — those hold values or pointers, not slot addresses. A stale value is
  worse than a missing one.
- **`ins.op_str` does not include the mnemonic.** Write operand regexes against
  `op_str` alone (`^([xw]\d+), \[([xw]\d+)(?:, #(0x[0-9a-f]+))?\]$`); a pattern
  that assumes the mnemonic is present matches nothing and looks like "no hits".
- Reuse one snapshot list for both the string-slot scan and the call trace —
  recomputing it per pass doubles the cost on large modules.
- Xref-scanning `.text` for the raw blob address frequently returns **0 hits** (aarch64 addressing is page-relative). When that happens, do not conclude the blob is unused — go through `__Pyx_InitCachedConstants` / `__Pyx_CreateCodeObjects` instead and recover `co_consts` tuples by tracking which slot index each `ldr` pulls from.

### Calls vs. operand loads (the TypeError trap)
A tracer that records only stringtab *loads* cannot tell `print(A + x + B)` from
`print(A + B)` followed by `x()` — both emit the same ordered slot sequence.
Resolve it from the instructions that follow the load:
- **Called:** the loaded name is followed by `mov x2, #-0x8000000000000000`
  (vectorcall nargs=1 with `PY_VECTORCALL_ARGUMENTS_OFFSET`), `mov x3, xzr`
  (kwnames = NULL), and a `bl` into the vectorcall stub. Emit `name()`.
- **Concatenated operand:** no such sequence; the value flows into
  `__Pyx_PyUnicode_Join`, whose operand count bounds how many strings take part.
- **Cross-check the join count.** Count `__Pyx_PyUnicode_Join` calls in the
  function and compare against the number of `+` expressions you plan to emit. A
  mismatch means one operand is a non-string global — usually a module function.
  Emitting `str + func` compiles cleanly and only raises
  `TypeError: can only concatenate str (not "function") to str` the first time
  the operator runs the file.
- **A module function may have no `__pyx_pf_*` symbol at all.** When
  `__pyx_pw_4<mod>_<n><func>` exists but the `__pyx_pf_*` twin does not, the wrapper
  *is* the implementation — disassemble the `pw` symbol for the body and read its
  tail (`mov x0, xzr`) to confirm it returns `None`. A `None` return is the
  positive signal that the name can only ever be a call target, never an operand.

### Parsing capstone text output
Do **not** `split(',')` on `ins.op_str`: memory operands and shift expressions contain commas inside brackets, which corrupts the token. Match operands with a regex such as `MEM = re.compile(r'\[(x\d+)(?:, #(0x[0-9a-f]+))?\]')`. For `add`, parse the destination with `DST = re.compile(r'^([xw]\d+),')` and only `int()` the immediate after stripping the `0x` — a register token like `x21` will otherwise raise.

## Get the module structure
Disassemble `__pyx_pymod_exec_<mod>` (the module-level body) and annotate it the same way. That single region yields the **exact import list and import order**, which is the skeleton the reconstructed source needs. Treat it as the whole module body, not just an import list: it also carries module-level assignments, compiled regex constants, colour/escape tables, hardcoded endpoint URLs, and the per-`__pyx_pf_*` call table. Every stringtab load in that region is a module global, so annotating it is how the reconstructed file's top-level constants get their exact values.

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

## Recover exact local-variable names from DWARF
When the target is **not stripped and carries `.debug_info`**, DWARF hands you the
original local/parameter names — this is the fidelity source for the
reconstruction, not the disassembly.
- Parse `.debug_str` / `DW_TAG_subprogram` with pyelftools. Cython exposes locals
  and params as `__pyx_v_<name>` in the subprogram DIE; strip the `__pyx_v_`
  prefix to get the source name. Guard `DW_TAG_subprogram` entries whose
  `DW_AT_name` is `None` (skip and descend into children) or the walk crashes.
- Pair each function's recovered local set with its `__pyx_pf_*` symbol to write
  bodies at source fidelity: paginator cursors, scraped tokens, and temp names
  all appear here and are otherwise invisible in the PLT trace.
- This **complements** the symbol inventory, it does not replace it — DWARF names
  the *inside* of a function; symbols and qualnames name its *boundary*.

## Pitfalls
- **Do not split `.rodata` on `\x00` and then require each chunk to be all-printable to find app strings.** CLI modules pack their literals with ANSI colour escapes and separator bytes, so the NUL-split-then-filter step silently drops every coloured string (they fail the all-printable test) and reads as "no strings". Extract `[\x20-\x7e]{3,}` runs from the raw section instead — see the mstate fallback in the string-table section.
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
- **Emitted signatures must be valid Python.** Cython emits a stringtab load only for a
  non-`None` default, so `__pyx_pf_*__defaults__` with one load means
  `def f(a='GET', b=None, c=None, ...)`, **not** `def f(a='GET', b, c, ...)` — a
  positional parameter after a defaulted one is a `SyntaxError`. Append `=None` to
  every parameter following the last explicit default; the compile gate only catches
  this if you actually run it.
- **A bytes-table entry can be a marshal blob, not a text constant.** When a
  `PyBytes_FromStringAndSize` length lands in the marshal range and the content
  starts with a code-object header, run `marshal.loads` on it: nested `class`/`def`
  bodies recover this way and are the only source for methods whose
  `__pyx_pf_*` symbol is absent from the table.
- **Gate the emitted file on a static undefined-name scan, not just
  `py_compile`.** `py_compile` happily accepts a body written from a constant
  trace that references a local you never defined; the operator's editor
  (`reportUndefinedVariable`) catches it first and the reconstruction reads as
  broken. Walk the emitted AST with a scope-aware visitor — or `symtable` — over
  the *whole file*, resolve every `ast.Name` load against enclosing-function
  params/assignments plus module globals and builtins, and fix or recover each
  miss before delivery. When the missing local is a scraped value (a hidden-form
  `jazoest`/`fb_dtsg` token, a pagination cursor), the regex or format string that
  produces it is already in the recovered string table — grep it there instead of
  inventing one.
- **Hand the reconstruction over as a file path, never as a code block.** The
  operator runs the artifact on their own machine, so it must be self-contained:
  write the `.py` and send the path. A code block forces a copy-paste that drops
  encoding-sensitive escapes.
- **Capstone 6.x moved the aarch64 constants.** `capstone.arm64` no longer
  re-exports `CS_ARCH_*`, and `Cs` is not reachable from the arch submodule.
  Import the top-level package (`import capstone as _cs`), set
  `CS_ARCH_ARM64 = _cs.CS_ARCH_AARCH64`, and build
  `_cs.Cs(CS_ARCH_ARM64, _cs.CS_MODE_LITTLE_ENDIAN)`.
- **Derive sleep/pacing granularity from the disassembly, not from the row count.**
  A `time.sleep` inside the row loop of a 97k-row dump is a multi-hour run; the
  original almost always paces per *request page*. Locate the sleep relative to
  the inner row loop before porting it, and state the resulting wall-clock cost
  when you report the reconstruction.
- **A reconstruction that never attached a live credential hides `ValueError` and
  `NameError` that only fire on the real path.** A parser written as
  `for uid, nm in rows` compiles and benches fine against synthetic data, then
  crashes the moment a real token makes the loop run. Exercise the loop end to
  end with a mocked network boundary and a dummy token before delivering.
- **Diff the reconstruction's class/method set against `nm` on the authoritative
  binary.** `__pyx_pf_*` mangling and the qualname strings (`U_xxx =
  'SomeClass.method'`) each enumerate the classes independently; a whole class
  the first pass missed shows up as a name present in the binary and absent from
  the emitted file. Method order in the binary is source order — use it to
  reorder the emitted class.
- **A module-level `def` is a call target, never a `print` operand.** When a name
  is both a recovered global constant and a `__pyx_pf_*` function, the call site
  is `name()`; emitting `print(name)` compiles cleanly and prints a function
  object at runtime.
- **Redact recovered credentials in both the emitted source and the report.**
  Cython modules routinely hardcode app tokens, cookies, and API keys in the
  string table. Replace the literal with `[REDACTED]` (keep its length and
  `id|secret` shape when that matters for the code to parse) and never paste the
  real value into the chat or the delivered file.

See `references/cython-blob-variants.md` for the compressed-blob decompressors, the per-module table/slot-base/mask comparison, and the co_consts tuple recovery recipe.

For free-threaded CPython (3.13t/3.14) modules — TLS-register mstate detection, the runtime-filled-slot boundary, the `__Pyx_InitConstants.cstring` data blob, and reloc-based name-table recovery — see `references/free-threaded-cython.md`.

Run `scripts/decode_cython_symbols.py` (accepts a `.so` or `nm` output) to turn
mangled `__pyx_pf_*` / `__pyx_pw_*` names into the module/class/method tree.

Once the string table is recovered and the remaining work is emitting runnable
`.py` modules across a repo, follow `references/generator-and-trace.md`: the
three-stage pipeline, the semantic-trace emission shape, the wrapper-vs-
implementation demangling, and the compile/coverage gate before packaging.

## Reconstruction confidence
- VERIFIED: function names (symbols), all constants, call targets (PLT/dynsym resolution), exception handlers.
- INFERRED: loop/menu bodies not directly visible — reconstruct the most consistent structure from the constants and label it as inferred.
- Capstone on cross-arch: `_cs.CS_ARCH_AARCH64`, never `CS_ARCH_ARM64` — see the 6.x pitfall above.
- SMOKE-TEST the finished file before reporting it done: `py_compile` proves syntax only. Import the module and exercise the pure helpers (parsers, regexes, UA generators, colour pickers, splitters) with asserted expected values taken from the recovered string table. Leave interactive entry points untriggered — call the helpers directly rather than `main()`/`menu()`. A reconstruction that compiles but returns wrong dicts is still wrong. Run the static undefined-name scan from Pitfalls first, and add a runtime pass over the reconstructed control flow (feed a recorded form page through the scraper, a sample cookie string through the parser) so  a `TypeError`/`NameError` surface before the operator hits it.
- **Mock the I/O boundary and assert on the artifact, not just on return values.**
  Patch the module's HTTP helper to return recorded pages (two 10k-row pages plus
  one empty page to terminate), attach a dummy token, and assert: request count,
  the first URL verbatim, lines written, the exact head line, and the field
  separator. This is what catches a wrong endpoint, a missing pagination break,
  and a malformed `_save()` — none of which a helper-level smoke test sees.
- **After any structural edit, re-grep the emitted source for the endpoint and
  status strings taken from the string table.** Deleting a "redundant" fallback
  branch is how `/subscribers?limit=10000` and `Server Timeout [` disappear from a
  reconstruction that still compiles cleanly.
