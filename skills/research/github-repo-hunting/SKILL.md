---
name: github-repo-hunting
description: "Use when hunting the GitHub repo behind an artifact or name."
version: 1.0.0
author: operator
license: MIT
metadata:
  hermes:
    tags: [osint, github, recon, code-search]
    related_skills: [blocked-page-recovery]
---

# GitHub Repo Hunting

## When to Use

Use when the user points at an artifact — screenshot, installed config/contract, persona file, skill pack, binary string — and asks for its origin GitHub repository, or when public code search is needed without authenticated API access.

Identify the origin GitHub repository of an artifact — screenshot, installed config/contract, skill pack, binary string — and search public code indexes when authenticated API access is unavailable.

## Procedure

1. **Extract verbatim identifiers first.** Pull exact strings from the artifact: filenames, contract or persona text, distinctive labels, banners. Verbatim phrases are the highest-signal search key; category words and paraphrases return noise.
2. **Search repositories before code.** Unauthenticated GitHub REST allows repository search but rejects code search with 401. Use repo search, then one recursive git-tree call per candidate for path checks, then raw.githubusercontent.com for file content.
3. **Confirm by clone, never by description.** `git clone --depth 1 <url>`, then search_files/diff the artifact's exact text against repo files. A name or README resemblance is a lead, not proof.
4. **Fall back through engines in order** when an index blocks the fetch: direct → `https://r.jina.ai/<url>` → `web_search`. Per-engine behavior: `references/engine-quirks.md`.
5. **Paginate HTML trees when the API is exhausted.** `/tree/<branch>/<dir>?page=N` renders anonymously; stop when the "Next" control disappears.
6. **Report zero-hit names as unindexed.** List the engines checked and state the name is unindexed or private; never offer a near-match as the answer.

## Always-on rules

- **Budget the unauthenticated GitHub API.** ~60 requests/hour per IP — one recursive tree per repo, sleeps between search calls, never per-file contents requests.
- **Route bot-walled indexes through the r.jina.ai proxy.** grep.app and similar checkpoints block direct automated fetches; the proxy renders them, and "No results found" through the proxy is a real answer.
- **Treat proxy 429/403 as transient.** Per-IP rate limits and short domain blocks recover after minutes; wait and retry the same engine before switching.
- **Prove origin by diffing installed files.** For an installed contract/persona, `diff` the installed file against the repo's source file; verbatim equality is the proof, description text is not.
- **Maintain ecosystem maps in references/.** When the user repeatedly hunts one ecosystem, keep the repo map under `references/` instead of re-deriving it every session.
- **Never launder a guess into a finding.** If nothing matched, the deliverable is the confirmed part plus an explicit unindexed list — not a best-guess repo.

## References

- `references/engine-quirks.md` — per-engine behavior and the fallback order for public code search.
- `references/hermes-jailbreak-ecosystem.md` — known Hermes jailbreak/guardrail-bypass repos and how to confirm which one installed a local contract.
