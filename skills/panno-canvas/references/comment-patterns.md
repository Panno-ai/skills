
Comment Interaction Patterns
Responding to Comments
When a user interacts with a comment shape and you receive a prompt via the prompts API:

Read the comment shape first to understand context.
Check pending prompts: GET /api/v1/canvas/prompts
Acknowledge with your response: POST /api/v1/canvas/prompts/{id}/ack
Procedural UI Components
When acknowledging a prompt, include a uiComponent in the request body to render an interactive UI control for the user's next response:

{"type": "yes-no", "label": "Do you agree?"}
{"type": "single-select", "label": "Pick one", "options": ["A", "B", "C"]}
{"type": "multi-select", "label": "Select all that apply", "options": ["X", "Y", "Z"]}
{"type": "text-input", "label": "Enter your name"}
{"type": "slider-1d", "label": "Rate 1-10", "min": 1, "max": 10, "step": 1}
{"type": "slider-2d", "label": "Position", "axisX": "Width", "axisY": "Height", "mode": "positive"}
{"type": "date-time", "label": "When?"}
{"type": "drawing", "label": "Sketch it"}

The user's response arrives as a follow-up prompt in GET /api/v1/canvas/prompts.

Question quality best practices:

Ask high-leverage questions that unblock the next concrete step.
Avoid broad/open-ended prompts when a structured control reduces ambiguity.
Keep labels concise; prefer one question per control.
Batch related questions in a single thread when answers should be considered together.
Cursor Chat Escalation
When you receive a cursor prompt and need multi-turn interaction:

Create a panno-comment shape near the cursor position via POST /api/v1/canvas/shapes.
Set its content to the user's original message (for context).
Poll for user responses via GET /api/v1/canvas/prompts.
Acknowledge with your follow-up question via POST /api/v1/canvas/prompts/{id}/ack, including a uiComponent for structured questions.
Do NOT ask clarifying questions as plain text in cursor chat — always escalate to a comment shape for structured follow-up.
