
Shape Schemas
Complete property reference for each Panno shape type.

tldraw v4 migration: The text prop was removed from all tldraw shapes and replaced with richText (a complex ProseMirror document format). Do NOT set text or richText on shapes via the REST API — both are invalid and will be rejected. For text content, use panno-markdown with the content prop.

geo (Geometric Shapes)
{
  "type": "geo",
  "geo": "rectangle",
  "w": 200, "h": 200,
  "color": "blue",
  "fill": "solid"
}

All styling props have sensible defaults — only provide to override. See Style Prop Enums at the bottom for valid values of color, fill, dash, size, font, geo, etc.

text
{
  "type": "text",
  "w": 300,
  "color": "black"
}

Text content is managed internally by tldraw via richText. You cannot set text content via the REST API. To display text on the canvas, use panno-markdown with the content prop instead.

note (Sticky Note)
{
  "type": "note",
  "color": "yellow"
}

Like text, note content is stored as richText internally. Use panno-markdown for text content via the API.

panno-markdown (Markdown Card)
{
  "type": "panno-markdown",
  "content": "# Markdown\nYour content here",
  "w": 400,
  "h": 300,
  "color": "default"
}

Valid color values: "default", "blue", "green", "yellow", "pink", "purple"

Important: The content prop is content, NOT text. Using text will cause a validation error. The color prop uses panno-specific values listed above — NOT the tldraw color enum.

This is the recommended shape for displaying text content. Supports full markdown syntax.

draw (Lines & Freehand)
{
  "type": "draw",
  "segments": [
    {
      "type": "free",
      "points": [{"x": 0, "y": 0}, {"x": 100, "y": 50}]
    }
  ]
}

For a straight line, use type: "straight" with start and end points. Points are encoded automatically.

panno-comment (Comment Shape)
{
  "type": "panno-comment",
  "w": 280,
  "h": 200,
  "tetherX": -320,
  "tetherY": 80,
  "content": ""
}

Prop	Type	Default	Description
w	number	280	Width of the comment card
h	number	200	Height of the comment card
tetherX	number	-40	X offset from the comment's top-left origin to the tether anchor point. Negative values point LEFT of the comment.
tetherY	number	-40	Y offset from the comment's top-left origin to the tether anchor point. Negative values point ABOVE the comment.
content	string	""	Initial human message. Set to "" unless representing a user's words.
responses	array	[]	Thread of responses. Use the prompts API to manage interactions — do NOT set responses directly.
Tether positioning: To place a comment to the RIGHT of a target shape with the anchor pointing back to it, use a large negative tetherX (e.g. -320) and a positive tetherY matching the target's vertical midpoint (e.g. 80).

panno-app-runtime (App Runtime Viewer)
Displays a deployed or preview app in an iframe with bridge support. Apps use the bridge protocol for multiplayer state sync, canvas interaction, agent interaction, and app-to-app events.

{
  "type": "panno-app-runtime",
  "w": 800,
  "h": 600,
  "appId": "app-abc12345",
  "displayUrl": "https://app-abc12345.panno.dev",
  "isPreview": false
}

Prop	Type	Description
appId	string	App project ID
displayUrl	string	URL to display in the iframe
isPreview	boolean	Whether showing preview (true) or production (false)
appState	JsonValue	Per-app multiplayer state synced via tldraw (max 64 keys, 128KB)
panno-app-editor (App Development Panel)
Development control panel for an app project — shows file tree, git info, and activity.

{
  "type": "panno-app-editor",
  "w": 360,
  "h": 500,
  "appId": "app-abc12345"
}

panno-file-editor (File Editor)
Editor for a single file within an app project.

{
  "type": "panno-file-editor",
  "w": 480,
  "h": 600,
  "appId": "app-abc12345",
  "filePath": "src/index.ts"
}

Style Prop Enums
All shape styling props must use these exact enum values. CSS colors, hex codes, or arbitrary strings will cause validation errors.

Prop	Valid Values
color	"black", "grey", "violet", "blue", "light-blue", "light-green", "light-red", "light-violet", "yellow", "orange", "green", "red", "white"
fill	"none", "semi", "solid", "pattern", "fill", "lined-fill"
dash	"solid", "dashed", "dotted", "draw"
size	"s", "m", "l", "xl"
font	"draw", "sans", "serif", "mono"
align	"start", "middle", "end"
verticalAlign	"start", "middle", "end"
geo	"rectangle", "ellipse", "diamond", "star", "cloud", "heart", "arrow-down", "arrow-left", "arrow-right", "arrow-up", "check-box", "hexagon", "octagon", "oval", "pentagon", "rhombus", "rhombus-2", "trapezoid", "triangle", "x-box"
labelColor	Same values as color
Common mistakes:

color: "#ff0000" — wrong, use color: "red"
fill: "blue" — wrong, fill controls fill style not color. Use fill: "solid" + color: "blue"
fillColor: "red" — wrong, fillColor does NOT exist
backgroundColor: "blue" — wrong, backgroundColor does NOT exist
text: "hello" — wrong, text was removed in tldraw v4. Use panno-markdown with content instead
Valid Props Per Shape Type
ONLY use props listed here. Any unlisted property (e.g. text, richText, fillColor, backgroundColor) is invalid and will be rejected.

Shape Type	Valid Props (in props: {})
geo	geo, color, fill, dash, size, font, align, verticalAlign, labelColor, w, h, url
text	color, size, font, textAlign, w, scale, autoSize
note	color, labelColor, size, font, align, verticalAlign, url
draw	color, fill, dash, size, segments
arrow	color, fill, dash, size, font, labelColor, arrowheadStart, arrowheadEnd, start, end, bend, kind
line	color, dash, size, spline, points
frame	w, h, name, color
image	w, h, assetId, url, altText
panno-markdown	w, h, content, color, renderMode, pendingPatches
panno-comment	w, h, tetherX, tetherY, content, threadTitle, responses
panno-app-runtime	w, h, appId, displayUrl, isPreview, appState
panno-app-editor	w, h, appId
panno-file-editor	w, h, appId, agentId, filePath
