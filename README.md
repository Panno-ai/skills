# Panno.ai Skills

Curated agent skills for Claude Code and other AI coding assistants. Each skill teaches Claude how to perform a specialized task — from generating reports to managing workflows — using nothing more than a folder of markdown instructions and optional scripts.

---

## Quick install

Copy any skill folder into your Claude skills directory:

```bash
# Clone the repo
git clone https://github.com/panno-ai/skills.git

# Copy a skill into your local Claude skills path
cp -r skills/llm-resource-usage ~/.claude/skills/
```

Claude Code will automatically detect and load installed skills at session start.

---

## Skills

| Skill | Description |
|---|---|
| [llm-resource-usage](skills/llm-resource-usage/) | Analyze your LLM usage across all local AI coding agents and generate an environmental impact report with infographic. |
| [panno-canvas](skills/panno-canvas/) | Interact with a Panno infinite canvas via REST API — create, read, and edit shapes using curl. |

---

## Skill format

Each skill is a self-contained folder:

```
skills/my-skill/
  SKILL.md          # Required. YAML frontmatter + markdown instructions.
  scripts/          # Optional. Executable scripts the skill invokes.
  references/       # Optional. Static data loaded into context when needed.
  assets/           # Optional. Files used in skill output.
```

### SKILL.md frontmatter

```yaml
---
name: my-skill
description: >
  What the skill does and when Claude should use it.
  Include key trigger phrases here.
---
```

Claude scans `name` and `description` (~100 tokens per skill) to decide relevance. Full instructions only load when the skill is triggered — so you can install many skills without impacting performance on unrelated tasks.

---

## Creating a new skill

1. Copy the template: `cp -r skills/template skills/your-skill-name`
2. Fill in the frontmatter (`name`, `description`) in `SKILL.md`
3. Write your instructions in the markdown body
4. Add scripts to `scripts/` and data to `references/` if needed
5. Test locally by installing the skill and triggering it in Claude Code

---

## Contributing

1. Fork this repository
2. Create a branch: `git checkout -b skills/my-skill-name`
3. Add your skill following the format above
4. Open a pull request with a brief description of what the skill does

**Rules:**
- Never put secrets, API keys, or credentials in SKILL.md or any skill file
- Keep SKILL.md under 5k tokens for the instructions section
- Scripts must be self-contained and not require global installs beyond common runtimes (Python 3, Node.js)

---

## License

MIT — see [LICENSE](LICENSE).
