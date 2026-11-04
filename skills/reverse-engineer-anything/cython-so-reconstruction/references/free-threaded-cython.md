# Free-threaded Cython .so (CPython 3.13t / 3.14)

Topical recipe for free-threaded CPython builds (e.g. aarch64 Cython 3.3.0 / CPython
3.14 Termux modules): detection, mstate addressing, name + literal recovery, and the
fidelity boundary. Companion to the mstate fallback and LZSS sections in SKILL.md.

## Detect the build
- ELF links `libpython3.14.so` / `libpython3.13t.so` and uses the free-threaded runtime.
- Disasm reads the TLS thread pointer: `mrs xN, tpidr_el0; ldr xN, [xN]` -> per-thread
  mstate; constants then load as `ldr xM, [xN, #off]`.
- Or a GOT indirection: `adrp x24,<page>; add x24,#imm` -> `__pyx_mstate_global` slot,
  then `ldr xN, [x24, #off]`. Both addressing styles can appear in one module.
- LTO often strips `__pyx_*` from `.symtab` (only ~10 survive) while `.debug_info`
  still holds the `__pyx_pf_*` / `__pyx_pw_*` DIEs. Use DWARF for function bounds
  (`DW_AT_high_pc` empty -> size = next `low_pc` - this `low_pc`) and original local
  names (`__pyx_v_<name>`). Guard subprogram DIEs whose `DW_AT_name` is None.

## Recover func/method names via relocs (no emulation)
`R_AARCH64_RELATIVE` = reloc type 1027. Build `{off: cstr(addend)}` for every reloc
whose **offset** falls inside the writable name-table region (contiguous, ~0x20-stride
entries). The addends point into `.rodata`; each is a `func_name` / method literal
(`mc`, `clear`, `load_proxies`, `XDMSX.check`, `dump.followers`, `menu`, ...). This
gives the full module/class/method tree without emulation or a live interpreter.

## Recover the literal pool
`readelf -sW <so>` and locate the `__Pyx_InitConstants.cstring` OBJECT symbol; its
`st_value` + `st_size` is the concatenated string-data blob that the char-pointer
table indexes into. Dump `[st_value, st_value+st_size)`. Literals are fragmented by
ANSI colour escapes and `0xff` separators: split on NUL, replace control bytes, and
join runs broken by `\x1b[...m`. This region holds menu text, regexes
(`(EAA[a-zA-Z0-9]+G)`, `name="fb_dtsg" type="hidden" value="(.*?)"`), endpoints
(`/v18.0/device/login`, `/subscribers?limit=10000`), UA templates, and fallback proxy
lists.

## The fidelity boundary (state it; do not fake it)
The interned-string slots referenced inside function bodies are runtime-filled:
**0 relocs with offset in the slot region, 0 structural `{slot,char_ptr,len}` records.**
A static 1:1 slot->text map requires emulating the import-time init routine (not
available offline for a cross-arch free-threaded build). Bind a slot's text only where
the instruction pattern plus the literal pool are unambiguous; otherwise emit the
operation trace, never invented statements. Byte-exact original source is NOT in the
binary (Cython -> ARM64 is one-way) — deliver grounded extraction + traces and say so
in one line, rather than shipping a plausible-looking reconstruction as "the decode".

## Tools that worked
- `pyelftools` for symbols / DWARF / relocs; `capstone` 6 with `CS_ARCH_AARCH64`
  (import top-level `import capstone as _cs; _cs.CS_ARCH_AARCH64`) for disasm.
- A stock `objdump` may lack aarch64 — drive capstone directly rather than relying on
  objdump operand annotations (its page-relative `adrp` notes are also unreliable for
  slot math; compute addresses from `adrp page + add imm` yourself).
