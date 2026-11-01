# DWARF source-line mapping and Cython API markers

Depth for the SKILL.md procedure. Load when the binary keeps `.debug_line` (most
non-stripped Cython builds do) — it turns structural guessing into reading.

## Section-aware `read()` helper

Aarch64 `adrp` pages do **not** align with section starts: a page at `0x3000` can
hold `.rodata.str1.1` while `.rodata` begins at `0x3200`. A single-section reader
silently returns empty bytes for every string reference on that page.

Build one resolver over all allocated, non-`NOBITS` sections and use it everywhere:

```python
secs = sorted([(s['sh_addr'], s['sh_addr'] + s['sh_size'], s['sh_offset'], s.name)
               for s in elf.iter_sections()
               if s['sh_addr'] and s['sh_type'] != 'SHT_NOBITS'])

def read(a, n):
    out = b''
    while n > 0:
        for lo, hi, off, _ in secs:
            if lo <= a < hi:
                take = min(n, hi - a)
                f.seek(off + (a - lo))
                out += f.read(take)
                a += take; n -= take
                break
        else:
            break            # unmapped hole — return what we have
    return out
```

Capstone on `.text` and `read()` on data sections then both work off the same map.

## DWARF line map

```python
from elftools.elf.elffile import ELFFile
dw = ELFFile(open(path, 'rb')).get_dwarf_info()
for cu in dw.iter_CUs():
    lp = dw.line_program_for_CU(cu)
    for e in lp.get_entries():
        if e.state and e.state.line:
            line_of[e.state.address] = e.state.line
```

- `DW_AT_decl_file` on a `DW_TAG_subprogram` names its source file; in a multi-file
  build this is what tells module A's function from module B's.
- `DW_AT_decl_line` gives the exact `def` line — the reliable way to split a class
  into methods when the symbol table is incomplete.
- Collapse consecutive equal lines **in address order**; the result is the source
  statement order.

## Filtering Cython-runtime line noise

The same CU carries the Cython runtime's own C line numbers. They recur constantly
and must not be read as Python source. Observed recurring set: `47, 131, 227, 282,
283, 288, 293, 313, 415, 420, 421, 513, 914, 2287, 7939, 7940, 7941, 7942, 8257,
8258, 8983, 8984, 8988, 9190, 9191, 9418, 9424, 9433, 9434, 9442, 9443, 9448, 9455,
9456, 9466, 9467, 9469, 9470, 9905, 9911, 9913, 13285, 13286, 13287`.

Rule: **keep only lines whose owning subprogram's `DW_AT_decl_file` is the target
`.py`.** Do not filter by numeric range — the real Python line numbers can be in the
tens of thousands in a generated file.

## Per-line semantic flow

Combine the line map with the PLT-resolved call trace into a one-line-per-source-line
summary, then read it top to bottom:

```
L3319: __Pyx_PyObject_FastCallDict
L3413: __Pyx_PyUnicode_Join
L4006: __Pyx__GetModuleGlobalName   <- x0='G'
L4351: __Pyx_PyObject_Append       <- x1='plist'
```

Build it by walking instructions in address order, emitting the resolved callee name
plus any live string-slot registers, and flushing the buffer whenever the mapped
source line changes.

### Register liveness (the recurring failure)
A stale slot index in a register produces a phantom string reference that survives
dozens of instructions — the same bogus value (e.g. `x11=' ['`) then repeats on every
subsequent line and misleads the whole reconstruction.

- Poison a register on **any** write that is not a known string-slot load.
- When reporting hits, take only the **most recently written** registers holding a
  slot index, and cross-check the claim against the mapped source line.
- A hit that repeats verbatim on >5 consecutive lines is almost certainly stale —
  drop it.

## Class structure without complete symbols

`nm` can omit `__pyx_pf_<...>` for class methods (static locals merged or stripped),
and a `pw` wrapper's `bl` may land on a shared trampoline rather than the body. Do
not depend on the symbol table for class layout. Recover it from:

- **qualname strings** in the interned-string table: `file.file_.file` decomposes as
  `module.class.method`; `file.file_.__init__` gives the constructor.
- `__Pyx_Py3ClassCreate` / `__Pyx_CyFunction_New` calls in `__pyx_pymod_exec_<mod>`,
  annotated with the `__init__` and method-name string slots.
- `__Pyx_mdef_4<mod>_<cls>_<meth>` symbols in `.data`, which pin the method order.

A class whose `__init__` body is unreachable this way still has its constructor
signature recoverable from the qualname plus the attribute-name string it stores.

## Import list

`__pyx_pymod_exec_<mod>` emits one `__Pyx_Import` per imported module and one
`__Pyx_ImportFrom` per imported name. Annotating both with the interned-string slots
yields the exact import block, including aliases (`from concurrent.futures import
ThreadPoolExecutor as ThreadPool` shows up as a global lookup for the alias name).

## Cython API markers -> Python constructs

These are the fastest structural tells in a semantic trace; each maps a Cython
helper back to a source-level construct.

| trace call | source construct |
|---|---|
| `__Pyx_PyObject_LookupSpecial('__enter__'/'__exit__')` | `with <expr>:` block |
| `__Pyx_IternextUnpackEndCheck` | `for a, b in <iter>:` tuple unpacking |
| `__Pyx_PyObject_Append` | `list.append(...)` |
| `__Pyx__PyUnicode_EqualsUCS4` | `== '<literal>'` (string compare) |
| `__Pyx__GetModuleGlobalName` | module-level global — an import or a module const |
| `__Pyx_GetBuiltinName` | builtin: `input`, `print`, `int`, `len`, `range`, `open` |
| `__Pyx_PyObject_FastCallDict` | a call; with no string arg it is usually `print(...)` |
| `__Pyx_PyObject_IsTrueAndDecref` | truthiness test (`if`, `while`, `and`/`or`) |
| `__Pyx_PyLong_AddObjC` | integer addition / counter increment |
| `__Pyx_PyObject_CompareBoolLt_int_int` | `<` comparison |
| `__Pyx_PyUnicode_Join` | `sep.join(...)` / implicit string concat |
| `__Pyx_AddTraceback` inside a loop body | a `try/except` guarding the loop body |
| `__Pyx__ExceptionSave` / `__ExceptionReset` | exception-path cleanup |

A run of `GetModuleGlobalName` for colour/constant names (`G`, `W`, `R`, `X`) followed
by `PyUnicode_Join` then `FastCallDict` is an f-string print.

