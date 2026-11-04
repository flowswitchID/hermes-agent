# Auditing an operator-supplied reconstructed reference tool

Use when the operator hands over a decompiled/reversed reference script
(CURL-XD / dmp.so family, `dmp_reversed.py` style) that errors at runtime, or
asks "cek error kenapa di file ini". The reconstruction is plausible-looking
but systematically wrong in a small set of ways. Audit for these BEFORE
porting behavior, and fix them in a delivered copy rather than explaining
prose-only.

## Bug class 1 — `print(<function>)` instead of `<function>()`

A helper that prints a separator (`linex()`, `banner()`) gets reconstructed as
an object reference: `print(linex)` renders `<function linex at 0x7f...>`
into the operator's terminal. Grep the file for `print(` followed by a bare
name that is defined locally as a function; every hit is a bug.

## Bug class 2 — platform-hardcoded output paths

`if not choice.startswith('/sdcard/'): choice = '/sdcard/' + choice` makes
`open()` raise on any non-Termux host, so every file prompt answers
"Invalid path ....!" forever. Replace with a normalizer that prefixes
`/sdcard/` only when the directory actually exists, otherwise resolves
against cwd; reject the bare `/sdcard` and `/sdcard/` inputs explicitly (the
reference recurses on them).

## Bug class 3 — unwired consumer attributes

The class that CONSUMES a token is constructed without receiving it from the
class that MINTS it (`dump.eaag_token` stays `None`, the request URL becomes
`access_token=None`, Graph API errors, `data` is empty, "Total : 0" — no
exception, just silence). Rule: for every `self.<attr>` read inside a method,
confirm the constructor or the caller sets it; wire the session's minted
token into the consumer at the call site and fail loudly ("token kosong")
instead of issuing a None-bearing request.

## Bug class 4 — validator reused on the wrong field

A UID validator (underscore/dash character-class check) gets reused as a NAME
filter. Names contain spaces, so entire lines are dropped, and in an
"emoji remover" the same check neither filters nor strips — emoji survive
verbatim. Rule: a validator named for one field must never filter another
field. Strip emoji with a Unicode-category filter (drop categories
So/Cs/Co/Cn/Cf plus the 0x1F000-0x1FAFF, 0x2600-0x27BF, 0xFE00-0xFE0F
ranges), keep letters/digits, then `.strip()`.

## Smoke-test recipe for interactive flows

Verify the fix without network and without a real cookie:

1. `import` the module (the `menu()` call must stay under `__main__`).
2. Feed prompts with `builtins.input = lambda *a, **k: next(iter_of_answers)`.
   Read the `input()` sequence in SOURCE order first — prompt order often
   differs from the menu order (file, count, output, then keywords).
3. Stub the network method (`_followers_loop`) and `menu()` to stop the
   interactive cascade; capture stdout with `io.StringIO`.
4. Assert the bug markers are ABSENT (`Invalid path`, `<function linex`)
   AND the happy path ran (stub received the right uid/path). Asserting only
   the happy path passes while the operator's original error still prints.

Deliver the fixed copy as a file (MEDIA: on Telegram) plus a short diagnosis
listing each bug class found — the operator pastes and runs.
