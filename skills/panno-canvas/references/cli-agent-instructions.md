
Panno REST API — CLI Agent Instructions
Use these instructions when interacting with Panno via HTTP/curl (REST API). If you have native read_canvas, create_shape tools available, use those instead.

Base URL
https://sync.panno.ai

Authentication
Check for credentials in this order:

PANNO_API_KEY env var — API key from web UI (recommended for production)
~/.config/panno/credentials.json — OAuth tokens from device flow sign-in
Guest session — zero-setup, temporary access
Option 1: API Key (recommended)
If $PANNO_API_KEY is set, use it as a Bearer token:

curl -X POST https://sync.panno.ai/api/v1/canvas/read \
  -H "Authorization: Bearer $PANNO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'

Option 2: OAuth Device Flow Sign-In
If no API key is available, initiate interactive sign-in.

Agent naming: The client_id identifies this agent connection in the Panno UI. Generate a unique name by combining your tool name with a distinguishing suffix:

"Cursor — projectname", "Claude Code — Bold Phoenix", "Windsurf (alice)"
Do NOT use generic names like "My Agent" — they will be duplicated across connections.
If unsure, ask the user what they'd like to call this connection.
# Step 1: Initiate device flow
curl -X POST https://sync.panno.ai/api/v1/auth/device \
  -H "Content-Type: application/json" \
  -d '{"client_id": "Cursor — myproject"}'

Response: { "user_code": "ABCD-1234", "verification_url": "https://panno.ai/authorize/device?code=...", "expires_in": 600 }

Tell the user: "Visit this URL to sign in: [verification_url]"

After the user approves and copies back the auth code:

# Step 2: Exchange auth code for tokens
curl -X POST https://sync.panno.ai/api/v1/auth/device/token \
  -H "Content-Type: application/json" \
  -d '{"auth_code": "USER_PASTED_CODE"}'

Response: { "access_token": "...", "refresh_token": "...", "token_type": "Bearer", "expires_in": 3600 }

Save tokens to ~/.config/panno/credentials.json:

{
  "access_token": "...",
  "refresh_token": "...",
  "expires_at": "2024-01-01T01:00:00Z"
}

Option 3: Guest Session (zero setup)
curl -X POST https://sync.panno.ai/api/v1/auth/guest \
  -H "Content-Type: application/json"

Response: { "access_token": "...", "room_id": "...", "room_url": "https://panno.ai/r/..." }

Tell the user: "A guest canvas has been created. View it at: [room_url]"

Guest sessions expire after 24 hours. The user can claim the canvas by logging in at the room URL.

Token Refresh
Access tokens expire after 1 hour. Refresh before expiry:

curl -X POST https://sync.panno.ai/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "rt_..."}'

Room Discovery
For multi-room agents, discover available rooms:

curl https://sync.panno.ai/api/v1/rooms \
  -H "Authorization: Bearer $TOKEN"

For single-room agents, the server automatically resolves the room. Pass room_id in request body only when you have multiple rooms.

API Endpoints
All endpoints return { "data": ... } on success or { "error": "..." } on failure.

Read Canvas
curl -X POST https://sync.panno.ai/api/v1/canvas/read \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

Optional filters: { "shapeTypes": ["text", "note"], "bounds": {"x":0,"y":0,"w":1000,"h":1000}, "shapeIds": ["shape:..."] }

Create Shape
curl -X POST https://sync.panno.ai/api/v1/canvas/shapes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "panno-markdown", "x": 100, "y": 100, "props": {"content": "# Hello World"}}'

Required: type, x, y. See references/shape-schemas.md for type-specific props.

Edit Shape
curl -X PATCH https://sync.panno.ai/api/v1/canvas/shapes/SHAPE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"props": {"content": "# Updated content"}}'

Delete Shapes
curl -X DELETE https://sync.panno.ai/api/v1/canvas/shapes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"shapeIds": ["shape:abc", "shape:def"]}'

Update Agent State
curl -X POST https://sync.panno.ai/api/v1/canvas/state \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state": "thinking", "message": "Analyzing code..."}'

States: idle, thinking, planning, reading, editing, searching

List Rooms
curl https://sync.panno.ai/api/v1/rooms \
  -H "Authorization: Bearer $TOKEN"

Create Room
curl -X POST https://sync.panno.ai/api/v1/rooms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Canvas"}'

Creates a new room owned by the authenticated user. The agent automatically joins the room. Returns { "data": { "ok": true, "room_id": "...", "name": "...", "room_url": "..." } }.

Important: Always share the room_url with the user so they can view the canvas in their browser.

Join Room
curl -X POST https://sync.panno.ai/api/v1/rooms/join \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"room_id": "ROOM_UUID"}'

Check Prompts
curl https://sync.panno.ai/api/v1/canvas/prompts \
  -H "Authorization: Bearer $TOKEN"

Acknowledge Prompt
curl -X POST https://sync.panno.ai/api/v1/canvas/prompts/PROMPT_ID/ack \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"response_text": "Done!"}'

Workflow
Authenticate — check env var, credentials file, or create guest session
Read first — always read canvas before editing to understand context
Create/edit shapes — use panno-markdown for rich content, note for quick items
Update state — set your agent state so users see your activity
Check prompts — periodically check for user prompts and acknowledge them
Troubleshooting
"No rooms available for this connection"
This means the agent has no rooms in scope. Causes and fixes:

OAuth agents (new sign-in): After sign-in, use GET /api/v1/rooms to discover your rooms. If you have no rooms yet, create one with POST /api/v1/rooms or join an existing one with POST /api/v1/rooms/join.
Guest agents: Guest tokens have the room baked into the JWT. If you see this error with a guest token, the token may have been incorrectly issued — re-create the guest session.
list_rooms returns empty array
This is expected for newly created OAuth agents. Rooms are not auto-created on sign-in. The agent can:

Create a new room via POST /api/v1/rooms
Join an existing room via POST /api/v1/rooms/join
Or use a guest session which auto-provisions a room
How room resolution works
Guest tokens: Room ID is embedded in the token. The server auto-resolves it — no room_id parameter needed in requests.
Single-room agents: The server resolves the room from the agent record. No room_id parameter needed.
Multi-room agents: You must pass room_id in each request body to specify which room to operate on.
