# Reading the compiled upstream (Cython .so tool family)

Use when the task is "make my tool behave like <upstream tool>" and the upstream
ships only compiled modules.

## Fetching

```
curl -s 'https://api.github.com/repos/<owner>/<repo>/git/trees/main?recursive=1'
# list blobs, then:
curl -sL https://raw.githubusercontent.com/<owner>/<repo>/main/<path> -o <file>
```

The interesting modules are usually the biggest / oddly-named ones (e.g. a
`core/fcrack.so` holding the dump engine, `utils/urls.so` holding endpoints).

## What plain `strings` gives you

Cython keeps function/var symbol names uncompressed:

```
strings -n 5 <file>.so | grep -E '__pyx_pf|__pyx_v_' | sort -u
```

`__pyx_pf_<mod>_<n>_<name>` maps function bodies (a module with
`S1_ S2_ S3_ S4_` is a staged pipeline); `__pyx_v_jazoest` / `__pyx_v_token`
reveal which auth material the engine uses. Short ALL-CAPS tokens
(`GRAPHQL`, `RFOLLOWS`) are obfuscated endpoint-name constants.

## What it does NOT give you

Python string constants are LZSS-compressed (the binary contains the error
string "LZSS string data decompression failed"), so `strings` never shows
`facebook.com`, `/friends`, `EAAG`, etc. Brute-forcing the LZSS variant is a
time sink — time-box it and fall back to:

1. Symbol names (above) for structure and auth flow.
2. Cookie-less `curl -sI` probes of candidate endpoints: 400 = alive but gated,
   302 → `/login` = login wall, 404 = dead. mbasic and www both answer 400
   cookie-less when alive.
3. Reimplement from the known-good recipe (see the parent SKILL.md procedure
   + `fb-html-dump-recipe.md`) and validate behavior, not byte-identical code.
