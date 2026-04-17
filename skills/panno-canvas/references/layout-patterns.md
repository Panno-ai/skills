
Layout Patterns
Best practices for arranging shapes on the Panno canvas without overlap.

Avoiding Overlap
Read first: Always read canvas with viewport bounds before placing shapes.
Offset from existing: Place new shapes at least 24px away from existing ones.
Snap to grid: Snap x/y coordinates to multiples of 24 for clean alignment.
Use cursor position: When available, place near the cursor with slight offset.
Viewport center fallback: If no cursor, use the center of the current viewport.
Recommended Shape Sizes
Use these minimum sizes for content-bearing shapes:

panno-markdown: w: 480, h: 400 (code content: w: 600)
panno-app-runtime: w: 800, h: 600
panno-app-editor: w: 360, h: 500
panno-file-editor: w: 480, h: 600
geo / note: w: 200, h: 200
Shapes auto-grow in height to fit content (up to 800px). Don't set shapes too small — scrolling is a worse user experience than a larger shape.

Grid Arrangement
For multiple related shapes (e.g., a list of cards):

Use a consistent grid with 24px gaps (matching the snap grid).
Flow left-to-right, then top-to-bottom.
Place new shapes to the right of or below existing shapes.
Compute placement: find the rightmost edge of nearby shapes, add 24px gap, place there.
Grouping Related Content
Place related shapes close together.
Use a larger gap (~72-96px, i.e., 3-4 grid units) between groups.
Consider using a geo shape as a background "container" for logical groups.
Flow & Diagrams
For flowcharts: top-to-bottom or left-to-right, consistent spacing.
For connections: use draw shapes with type: "straight" between center points of connected shapes.
Typical node spacing: 264px horizontal (11 grid units), 144px vertical (6 grid units).
Responsive Placement
Check viewportBounds to stay within the visible area.
For long content, place below existing shapes rather than beside them.
Leave room for the user to navigate — don't fill the entire viewport.
Quadrant Placement
When a canvas already has shapes and you need to add more:

Compute the bounding box of all existing viewport shapes (min x/y to max x/y+w/h).
Prefer right: place the new shape at maxX + 48 if the shape width fits within viewport bounds.
Fall back below: if horizontal space is insufficient, place at maxY + 48, left-aligned to the existing group.
Never place new content at the exact center of the viewport — that's where the user is looking.
For multi-shape additions, place the entire group as a unit (right or below), then arrange within the group using the grid rules above.
Flow Direction Awareness
Relationship	Direction	Spacing
Sequential steps (1 → 2 → 3)	Left-to-right	264px horizontal
Hierarchy (parent → children)	Top-to-bottom	144px vertical
Peer group (option A / B / C)	Same row	24–48px gap
Before / after comparison	Left-to-right	96px gap
Group Boundary Awareness
When adding a shape that belongs to an existing logical group (e.g., a new task for an existing plan):

Read the existing group shapes to get their bounding box.
Place the new shape adjacent to the group — outside the bounding box with a 24–48px gap.
Do not place shapes inside an existing geo background container unless you know its purpose.
