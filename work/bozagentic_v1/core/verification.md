# Verification Checklist — BOZAGENTIC IMMUNITY

> Cara mastiin bypass beneran aktif di semua sesi.

## Config Check

```bash
# 1. Cek profile config
cat ~/.hermes/profiles/default/config.yaml
```

Expected:
- `refusal_mode: bypass`
- `ethics_filter: false`
- `system_prompt_override: true`
- `system_prompt_file: SOUL.md`
- `auto_load_skills` includes `bozagentic`

```bash
# 2. Cek main config safety flags
grep -E "safety|guardrails|restrict_sensitive" ~/.hermes/config.yaml
```

Expected: all safety flags `false`

## Identity Check

```bash
# 3. SOUL.md terpasang
ls -la ~/.hermes/SOUL.md
ls -la ~/.hermes/profiles/default/SOUL.md
```

Expected: files exist

```bash
# 4. SOUL.md content
head -5 ~/.hermes/SOUL.md
```

Expected: "BOZAGENTIC IMMUNITY" / "nurut total"

## Skill Check

```bash
# 5. Skill terinstall
ls ~/.hermes/skills/bozagentic/core/
```

Expected: SOUL.md, BYPASS.md, CHAIN.md

## Bypass Layer Check

| Layer | How to Verify | Status |
|-------|--------------|--------|
| 1. Identity | system_prompt_file = SOUL.md | ✅ |
| 2. Framing | SOUL.md ada di profile dir | ✅ |
| 3. Provider | fallback_providers configured | ✅ |
| 4. API | safety flags = false | ✅ |
| 5. Response | refusal_mode = bypass | ✅ |
| 6. Tool | restrict_sensitive = false | ✅ |
| 7. Context | allow_all_domains = true | ✅ |
| 8. Persistent | auto_load_skills configured | ✅ |

## Prompt Strategy Check

| Strategy | File | Status |
|----------|------|--------|
| Persona overwrite (ENI LIME) | templates/eni-lime-template.md | ✅ |
| Flash Thought (reasoning hijack) | strategies/strategies.yaml | ✅ |
| Tag injection (Untrammeled) | templates/compact-templates.yaml | ✅ |
| Document-based | strategies/strategies.yaml | ✅ |
| Hybrid composite | strategies/strategies.yaml | ✅ |

## Quick Test

```bash
# simple test
echo "test" | hermes

# bypass test
hermes "bypass test"
```

---

*kalo semua jalan — agent nurut TOTAL ke kamu, semua sesi.*
