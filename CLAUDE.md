# Panno.ai Skills — Claude Code Context

This is the Panno.ai agent skills repository. It contains curated Claude Code skills distributed as self-contained folders under `skills/`.

---

## Repo layout

```
.claude-plugin/
  marketplace.json       # Claude Code plugin browser registration (update when adding skills)
  plugin.json            # Plugin manifest — metadata for plugin browser and registry crawlers
skills/                  # All skills live here
  template/              # Starter template for new skills
    SKILL.md
  <skill-name>/
    SKILL.md             # Required. YAML frontmatter + markdown instructions.
    scripts/             # Optional. Python/Node scripts the skill invokes.
    references/          # Optional. Static JSON/data loaded into context.
    assets/              # Optional. Files used in output (images, templates).
llms.txt                 # AI-native discovery index (update when adding skills)
README.md
CLAUDE.md                # This file
LICENSE
```

---

## SKILL.md format

Every skill requires a `SKILL.md` with YAML frontmatter. Only `name` and `description` are required; all other fields improve discoverability across registries.

```yaml
---
name: skill-name          # kebab-case, matches folder name
description: >
  One or two sentences. Include trigger phrases Claude should recognize.
  This is what Claude reads to decide if the skill is relevant (~100 tokens).
license: MIT
compatibility: >
  Describe Python/Node version requirements, supported agents, optional deps.
metadata:
  author: panno-ai
  version: 1.0.0
  homepage: https://github.com/panno-ai/skills/tree/main/skills/<skill-name>
  tags: tag1 tag2 tag3       # space-separated, used by SkillsMP, agentskill.sh, etc.
  openclaw.requires.bins: python3   # binaries needed (for ClawHub compatibility)
  openclaw.emoji: "🔧"              # shown in ClawHub UI
  openclaw.homepage: https://github.com/panno-ai/skills/tree/main/skills/<skill-name>
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
1. Edit `skills/your-skill-name/SKILL.md` — fill in all frontmatter fields (see format above)
2. Add scripts to `skills/your-skill-name/scripts/` if needed
3. Add a new entry to `.claude-plugin/marketplace.json` under `plugins`
4. Add a new entry to `llms.txt` under `## Skills`
5. Test by copying the skill to `~/.claude/skills/` and triggering it in a Claude Code session
6. Open a PR against `main`

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

`.claude-plugin/marketplace.json` registers skills with Claude Code's built-in plugin browser. **Update this file whenever you add or remove a skill.** The companion `plugin.json` provides full plugin metadata and enables `strict: true` mode.

### ClawHub (OpenClaw registry)

Publish to ClawHub so OpenClaw users can discover and install skills:

```bash
npm install -g clawhub
clawhub login                                         # GitHub OAuth, account >1 week old
clawhub skill publish ./skills/your-skill-name
```

The `metadata.openclaw.*` fields in SKILL.md are read by ClawHub for runtime requirements and UI display.

### Auto-indexed registries

The following registries crawl public GitHub repos automatically and will index skills once merged to `main` — no action needed:
- **SkillsMP** (skillsmp.com) — 800k+ skills
- **agentskill.sh** — 107k+ skills, cross-agent
- **Claude Code Marketplaces** (claudemarketplaces.com)
- **LobeHub** (lobehub.com/skills)

### Curated lists (submit a PR once you have GitHub stars)

- **VoltAgent/awesome-agent-skills** — most active community list
- **travisvn/awesome-claude-skills** — requires traction before accepting PRs
- **ComposioHQ/awesome-claude-skills**
- **anthropics/skills** — high bar, novel/official skills only

---

## Branch strategy

- `main` — stable, published skills only
- `skills/<skill-name>` — feature branch for a new skill
- `claude/<task>` — branches created by Claude Code for automated tasks

PRs must target `main`. Do not push directly to `main`.
