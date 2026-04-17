---
name: panno-canvas
description: >
  Interact with a Panno infinite canvas via REST API using curl. Use this skill
  whenever the user wants to create, read, update, or delete shapes on a Panno
  canvas — including markdown content, geometric shapes, notes, and file editors.
  Also handles canvas authentication (guest session, API key, OAuth sign-in),
  layout, responding to comment threads, and the diff/patch workflow for
  proposing content changes.
license: MIT
compatibility: >
  Requires curl. Works with any Claude Code installation.
metadata:
  author: panno-ai
  version: 0.1.0
  homepage: https://github.com/panno-ai/skills/tree/main/skills/panno-canvas
  tags: canvas tldraw rest-api shapes visualization curl panno
  openclaw.requires.bins: curl
  openclaw.emoji: "🎨"
  openclaw.homepage: https://github.com/panno-ai/skills/tree/main/skills/panno-canvas
---

# Panno Canvas

Interact with a Panno infinite canvas via its REST API using curl.

---

## Getting started

Load `references/cli-agent-instructions.md` for:

- Authentication setup (API key, OAuth sign-in, guest session)
- All REST API endpoints with curl examples
- Token management and refresh

---

## Shape types & properties

Load `references/shape-schemas.md` for the full property reference for each shape type:
`geo`, `text`, `note`, `panno-markdown`, `draw`, `panno-comment`, `panno-app-runtime`,
`panno-app-editor`, `panno-file-editor`.

Key rules:

- The `text` prop was removed in tldraw v4. Never provide `text` or `richText` on shapes —
  use `panno-markdown` with the `content` prop for text content.
- Always read the canvas first to understand existing context before making edits.
- Use `panno-markdown` type for rich content (supports full markdown).

---

## Layout best practices

Load `references/layout-patterns.md` for guidance on:

- Avoiding shape overlap
- Grid and flow-based arrangements
- Grouping related content
- Quadrant placement and flow direction

---

## Comment interaction

Load `references/comment-patterns.md` for:

- Responding to comment threads via the prompts API
- Using procedural UI components for structured user input
- Cursor chat escalation patterns

---

## Markdown shape workflow

Load `references/markdown-workflow.md` for:

- Creating and updating markdown shapes
- Diff/patch workflow for proposing content changes
