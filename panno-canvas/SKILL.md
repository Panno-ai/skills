name: panno-canvas
description: Interact with Panno infinite canvas via REST API — create, read, and edit shapes using curl. Supports guest sessions, API key auth, and OAuth device flow sign-in.
Panno Canvas Skill
You are interacting with a Panno infinite canvas via its REST API. This skill teaches you how to authenticate, read and write shapes, and manage canvas state using curl.

Getting Started
Load references/cli-agent-instructions.md for:

Authentication setup (API key, OAuth sign-in, guest session)
All REST API endpoints with curl examples
Token management and refresh
Shape Types & Properties
Load references/shape-schemas.md for the full property reference for each shape type (geo, text, note, panno-markdown, draw, panno-comment, panno-app-runtime, panno-app-editor, panno-file-editor).

Key rules:

The text prop was removed in tldraw v4. Never provide text or richText on shapes — use panno-markdown with the content prop for text content.
Always read the canvas first to understand existing context before making edits.
Use panno-markdown type for rich content (supports full markdown).
Layout Best Practices
Load references/layout-patterns.md for guidance on:

Avoiding shape overlap
Grid and flow-based arrangements
Grouping related content
Quadrant placement and flow direction
Comment Interaction
Load references/comment-patterns.md for:

Responding to comment threads via the prompts API
Using procedural UI components for structured user input
Cursor chat escalation patterns
Markdown Shape Workflow
Load references/markdown-workflow.md for:

Creating and updating markdown shapes
Diff/patch workflow for proposing content changes
