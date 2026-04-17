
Markdown Shape Workflow
Creating Markdown Content
For substantive answers (from command bar or chat panel):

Create a shape with type panno-markdown near the cursor position.
Edit it to update its content prop with your full markdown response.
For long responses, PATCH the shape multiple times — each call replaces the entire content prop.
Diff/Patch Workflow
To propose changes to existing markdown content:

{
  "pendingPatches": [
    {
      "id": "patch-unique-id",
      "original": "old text",
      "proposed": "new text",
      "status": "pending"
    }
  ]
}

Important rules:

The original field must match the raw markdown source exactly (not rendered HTML).
Use **bold** not bold
Use # Heading not Heading
The user sees inline diffs and can accept or reject each patch.
Do NOT modify the content prop when proposing patches — only set pendingPatches.
