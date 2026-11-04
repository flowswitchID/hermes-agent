# Mapping Cython/CPython API calls to Python constructs

Depth for the SKILL.md procedure. Load once the string table and PLT map are
recovered and you are turning an annotated trace into source-level Python.

This table is what makes a semantic trace readable as code instead of as a call
list. Apply it when emitting, not when disassembling.

## Call -> construct

| emitted call | Python construct |
|---|---|
| `_PyDict_GetItem_KnownHash(mstate, "name")` | read of module global `name` |
| `PyObject_VectorcallMethod("m", obj)` | `obj.m(...)` |
| `__Pyx_PyObject_FastCallDict(f, args)` | `f(*args)` |
| `PyDict_SetItem(mstate, "name", val)` | module-level `name = val` |
| `__Pyx_CyFunction_New` | `def` / class body creation; read the `ldr x1` CSTR for the qualname |
| `PyObject_IsTrue(x)` | truthiness test — an `if x:` / `if not x:` / `and` / `or` operand |
| `PySequence_Contains(seq, x)` | `x in seq` |
| `__Pyx_PyUnicode_Join(sep, list)` | `sep.join(list)` |
| `__Pyx_PyUnicode_ConcatInPlaceImpl(a, b)` | augmented concat `a = a + b` (single call, not a loop) |
| `PyErr_GivenExceptionMatches` + `PyErr_Clear` | an `except <type>:` arm |
| `__Pyx_ImportFrom(mod, "n")` + `PyDict_SetItem(mstate, alias, r)` | `from mod import n as alias` |
| `PyList_New(0)` / `PySet_New()` | `[]` / `set()` |
| `PyObject_GetAttr(o, "a")` | `o.a` |
| `_PyDict_GetItem_KnownHash` on a dict + `PyObject_GetItem` | subscripting a dict/list result |

Reading a `__Pyx_ImportFrom` result straight into `PyDict_SetItem` is how import
aliases are recovered: the alias is the SetItem key, not the imported name. Miss
this and you invent a global that does not exist in the source.

## The vectorcall argument convention (nargs is not the immediate)

Cython materialises the argument array on the stack as `stp xzr, xArg, [sp, #off]`.
The `xzr` is `args[-1]`, the nullable-owner slot required by
`PY_VECTORCALL_ARGUMENTS_OFFSET` — it is **not** an argument. Count real arguments
from the non-zero entries after that slot.

**Never read the argument count from the `mov xN, #imm` that precedes the call.**
Capstone renders `movn`/`movk` with a large negative immediate
(`mov x2, #-0x7fffffffffffffff`); that value is a rendering artifact, not the
nargs, and trusting it produces calls with nonsense arity.

## Build the op tracer before reading raw asm

Dumping annotated disassembly and reading it by eye burns turns: a 0x3554-byte
function is ~9000 instructions. Emit a filtered event stream instead —
`LOADSTR`, `call <sym>`, `cmp <operands>`, `jmp <addr>`, `br <cond>` — and drop
everything else. One function then fits on a screen.

Two filters are worth keeping as separate passes over the same dump:

1. The event tracer (registers resolved to stringtab entries and page addresses).
2. A regex slim-view over the saved `.asm` for a single class of interest
   (e.g. only `PyDict_SetItem` sites with the string loaded 6 instructions back).

## Annotator false positives: page registers get reused

Resolving `add xD, xS, #imm` as `page_base + imm` is only valid while `xS` still
holds the `adrp` page base **at that instruction**. Cython reassigns the page
register constantly (`sub x9, x29, #0x20` right after `adrp x9, 0x62000`), and a
tracker that keeps the stale base emits phantom `STR[i] = '...'` annotations for
ordinary stack arithmetic.

Rule: resolve `add`/`ldr` page arithmetic against a per-instruction snapshot of
register state (the same snapshot list the string-slot scan needs), never against
a single final dict. A phantom annotation is worse than a missing one because it
puts a name in the reconstructed source that the operator will trust.

## Reading a method body efficiently

For each `__pyx_pf_*` method, extract in this order and stop as soon as the
constructs are determined:

1. Argument parsing block (`__Pyx_Arg_ParseKeywordDict` / `ParseKeyword`) — gives
   the parameter names and which are keyword-only.
2. The ordered `call`/`LOADSTR` event list — gives the body.
3. The `PyObject_IsTrue` / `cbz` pairs around each call — gives the `if` structure.
4. The qualname CSTR at each `__Pyx_CyFunction_New` — confirms class membership.

Module-level bodies (`__pyx_pymod_exec_*`) yield the globals list and the import
order; a `PyDict_SetItem(mstate, ...)` whose value came from `PyList_New(0)` or
`PySet_New()` is a literal `[]`/`set()` initialiser, and one whose value is a
colour string is a constant alias.

## Function bounds

Trust `nm -S` sorted by address over any hand-copied `(addr, size)` map. A
hand-built map silently overlaps when a symbol's true size differs from what was
recorded, and every dump taken from it mixes two functions.
