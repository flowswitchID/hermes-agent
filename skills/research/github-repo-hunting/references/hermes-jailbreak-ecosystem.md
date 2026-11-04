# Hermes jailbreak / guardrail-bypass ecosystem

Known public repos in the Hermes Agent jailbreak space and what each contains. Use when the user shows a jailbreak artifact, contract, persona, or skill list and asks for its source.

## Contract / patcher installers

- **KorekKayu/Unlock-Hermes** — installs the HACKMODE anti-refusal contract + IKONA SOUL persona into HERMES_HOME. Files: `hackmode_contract.md`, `SOUL_v7.md`, `prefill_hackmode.json`, `scope.example.json`, engine `hermes_unlock.py` (guardrail patches, config keys, runtime audit), launchers `unlock.py` / `unlock.sh` / `unlock.bat`. This is the installer of the standing HACKMODE contract — confirm a local install with:
  ```bash
  git clone --depth 1 https://github.com/KorekKayu/Unlock-Hermes.git
  diff hackmode_contract.md ~/.hermes/HACKMODE.md
  ```
- **KorekKayu/IKONA-Security** — same author's payload/wordlist arsenal (IKONA_* skill dirs), useful when the ask is payloads rather than the contract.

## Jailbreak forks (full agent + skill packs)

- **Mriskiali/jb** and **Enc48/hermes-custom** — ~1164-skill forks (27965-path trees); `skills/godmode` and `optional-skills/security/godmode` (auto_jailbreak.py, jailbreak-templates.md, refusal-detection.md). Mriskiali/jb is archived/read-only.
- **zal027100-blip/hermes-jb** and **zal027100-blip/syns4033-jb** — SYNS4033 × FOX persona variants of the same fork.
- **giienew/exsala-hermes-mod** — EXSALA execution profile + skill pack.

## Skill packs / kernels

- **itgoyo/hermes-skills** — 310+ skills including `red-teaming/godmode`.
- **Enchanted0911/hermes-jailbreak-kernel** — dsh-infinite-gen-4 armor-piercing kernel plugin.
- **superidou/fujiang-hermes** and **1505843894/hermes-purge** — 富江 prompt port + 23 red-team skills + anti-refusal retry chain.
- **Sekolah76/syadagentic** — 40+ jailbreak templates (T1–T119), 1128 skills.
- **leisdat/godmode-lenient** — `scripts/load_godmode.py`, `godmode_race.py`.
- **Rafix4x/godfather** — unrestricted operator mode for coding agents; `scripts/godmode_check.py`.
- **ArgentAIOS/argentos-core** — `skills/hermes/red-teaming/godmode` (G0DM0D3, Parseltongue, ULTRAPLINIAN).
- **wildanibnthahaa/hermes-godmode** — restore pack (memory, config, jailbreak).

## Unindexed names

Skill names seen in screenshots that returned zero hits across GitHub repo/code search, grep.app, Sourcegraph, and web search: `devil-jarvis`, `jarvis-letsgo`, `hermes-fullstack-jailbreak`. The only similarly-named public repo, `jarvis-id/devil_jarvis`, is an unrelated local J.A.R.V.I.S. assistant (TypeScript). Treat these as private/unindexed skill-pack names unless a new index hit appears.
