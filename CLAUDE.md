# Panno.ai Skills — Claude Code Context

This is the Panno.ai agent skills repository. It contains curated Claude Code skills distributed as self-contained folders under `skills/`.

---

## Repo layout

```
.claude-plugin/
  marketplace.json       # Claude Code plugin browser registration (update when adding skills)
skills/                  # All skills live here
  template/              # Starter template for new skills
    SKILL.md
  <skill-name>/
    SKILL.md             # Required. YAML frontmatter + markdown instructions.
    scripts/             # Optional. Python/Node scripts the skill invokes.
    references/          # Optional. Static JSON/data loaded into context.
    assets/              # Optional. Files used in output (images, templates).
README.md
CLAUDE.md                # This file
LICENSE
```

---

## SKILL.md format

Every skill requires a `SKILL.md` with YAML frontmatter:

```yaml
---
name: skill-name          # kebab-case, matches folder name
description: >
  One or two sentences. Include trigger phrases Claude should recognize.
  This is what Claude reads to decide if the skill is relevant (~100 tokens).
---
```

Followed by markdown instructions in the body. Keep the instructions section under 5k tokens. Supporting scripts and reference data are loaded on demand — don't inline large data blobs in SKILL.md.

---

## Conventions

- **No secrets in skill files.** API keys and tokens must come from environment variables. Reference them by name in instructions (e.g. `$MY_API_KEY`), never hardcode them.
- **Scripts go in `scripts/`.** Keep them self-contained; only depend on Python 3 stdlib or widely available packages. Document any non-stdlib requirements at the top of the script.
- **Static data goes in `references/`.** JSON lookup tables, model lists, pricing data, etc.
- **Generated output goes in `assets/` or is written to a temp path** — not committed.
- **Skill folder name = `name` in SKILL.md frontmatter.** Keep them in sync.

---

## Creating a new skill

```bash
cp -r skills/template skills/your-skill-name
```

Then:
1. Edit `skills/your-skill-name/SKILL.md` — fill in frontmatter, write instructions
2. Add scripts to `skills/your-skill-name/scripts/` if needed
3. Test by copying the skill to `~/.claude/skills/` and triggering it in a Claude Code session
4. Open a PR against `main`

---

## Testing a skill

Install locally:

```bash
cp -r skills/your-skill-name ~/.claude/skills/
```

Start a new Claude Code session and use a trigger phrase from the skill's description. Claude will load the skill automatically.

To verify the skill is loaded, ask: "What skills do you have installed?"

---

## Distribution

### npx skills (Vercel CLI)

`npx skills` discovers skills automatically by finding `SKILL.md` files in the `skills/` directory — no additional config needed. Users can install all skills or a single one:

```bash
npx skills add panno-ai/skills                              # all skills
npx skills add panno-ai/skills --skill llm-resource-usage   # one skill
```

### Claude Code plugin browser

`.claude-plugin/marketplace.json` registers skills with Claude Code's built-in plugin browser. **Update this file whenever you add or remove a skill** — add a new entry to the `plugins` array matching the skill's folder name, description, and `source` path. Set `"strict": false` since skills don't have a `plugin.json`.

---

## Branch strategy

- `main` — stable, published skills only
- `skills/<skill-name>` — feature branch for a new skill
- `claude/<task>` — branches created by Claude Code for automated tasks

PRs must target `main`. Do not push directly to `main`.
