"""
Chess Card — LiPo Pocket + Milling Annotation
==============================================
Run in KiCad Scripting Console:
    exec(open("C:/path/to/add_lipo_pocket.py").read())

What this does:
  1. Removes any previous pocket rectangles / text on User.1 and B.Fab
  2. Draws a closed 35.5 x 30.5 mm rectangle on B.Fab (visible in 3D, 
     exported in fab Gerber — JLCPCB reads this as the milling boundary)
  3. Draws the same rectangle on User.1 as a cross-check layer
  4. Adds a text callout on B.Fab: "Pocket 0.4mm deep"
  5. Adds a courtyard exclusion so DRC doesn't complain about the LiPo

Pocket dimensions:
  LiPo cell: 35 x 30 mm (EEMB LP503035)
  Pocket:    35.5 x 30.5 mm (0.25mm clearance each side)
  Position:  x=5, y=27 from card top-left corner (board origin 100,100)
"""

import pcbnew

BOARD_ORIGIN_X = 100.0
BOARD_ORIGIN_Y = 100.0

# Pocket position relative to card top-left corner (mm)
POCKET_X      = 5.0      # left edge of pocket
POCKET_Y      = 27.0     # top edge of pocket
POCKET_W      = 35.5     # width
POCKET_H      = 30.5     # height
POCKET_DEPTH  = 0.4      # mm (instruction only — not enforced by KiCad geometry)

def mm(v):
    return pcbnew.FromMM(v)

def abs_x(rel_x):
    return mm(BOARD_ORIGIN_X + rel_x)

def abs_y(rel_y):
    return mm(BOARD_ORIGIN_Y + rel_y)

board = pcbnew.GetBoard()

# ── 1. Clean up previous pocket drawings ──────────────────────────────────────
removed = 0
for item in list(board.GetDrawings()):
    layer = item.GetLayer()
    if layer in (pcbnew.User_1, pcbnew.B_Fab, pcbnew.B_CrtYd):
        # Only remove items we likely placed (text containing "ocket" or "illing",
        # or shapes within the pocket bounding box)
        try:
            txt = item.GetText()
            if any(k in txt for k in ("ocket", "illing", "0.4mm", "Depth")):
                board.Remove(item)
                removed += 1
                continue
        except AttributeError:
            pass
        # Remove shapes that sit inside the pocket region
        try:
            pos = item.GetPosition()
            rx = pcbnew.ToMM(pos.x) - BOARD_ORIGIN_X
            ry = pcbnew.ToMM(pos.y) - BOARD_ORIGIN_Y
            if (POCKET_X - 2 <= rx <= POCKET_X + POCKET_W + 2 and
                    POCKET_Y - 2 <= ry <= POCKET_Y + POCKET_H + 2):
                board.Remove(item)
                removed += 1
        except Exception:
            pass

print(f"Removed {removed} old pocket items.")

# ── 2. Helper: draw a closed rectangle on a given layer ───────────────────────
def draw_rect(x, y, w, h, layer, line_width_mm=0.1):
    """Draw 4 segments forming a closed rectangle."""
    corners = [
        (x,   y),
        (x+w, y),
        (x+w, y+h),
        (x,   y+h),
    ]
    for i in range(4):
        x1, y1 = corners[i]
        x2, y2 = corners[(i+1) % 4]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(layer)
        seg.SetWidth(mm(line_width_mm))
        seg.SetStart(pcbnew.VECTOR2I(abs_x(x1), abs_y(y1)))
        seg.SetEnd(  pcbnew.VECTOR2I(abs_x(x2), abs_y(y2)))
        board.Add(seg)

# ── 3. Draw pocket on B.Fab (this is what JLCPCB uses for milling) ────────────
draw_rect(POCKET_X, POCKET_Y, POCKET_W, POCKET_H, pcbnew.B_Fab, line_width_mm=0.1)
print(f"Drew pocket rectangle on B.Fab  ({POCKET_W}x{POCKET_H}mm at card x={POCKET_X}, y={POCKET_Y})")

# ── 4. Draw the same rectangle on User.1 (cross-check / notes layer) ──────────
draw_rect(POCKET_X, POCKET_Y, POCKET_W, POCKET_H, pcbnew.User_1, line_width_mm=0.05)
print("Drew pocket rectangle on User.1")

# ── 5. Add milling depth callout text on B.Fab ───────────────────────────────
txt = pcbnew.PCB_TEXT(board)
txt.SetLayer(pcbnew.B_Fab)
txt.SetText(f"LiPo pocket — mill {POCKET_DEPTH}mm deep\n{POCKET_W}x{POCKET_H}mm")
txt.SetPosition(pcbnew.VECTOR2I(
    abs_x(POCKET_X + POCKET_W / 2),
    abs_y(POCKET_Y + POCKET_H + 2.5)
))
txt.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
txt.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
board.Add(txt)
print("Added depth callout text on B.Fab")

# ── 6. Add courtyard rectangle (tells DRC nothing should be placed inside) ────
draw_rect(POCKET_X, POCKET_Y, POCKET_W, POCKET_H, pcbnew.B_CrtYd, line_width_mm=0.05)
print("Added courtyard exclusion on B.CrtYd")

# ── 7. Save and refresh ───────────────────────────────────────────────────────
pcbnew.Refresh()
print("\nDone. Switch to B.Fab layer to verify pocket outline.")
print("In 3D viewer: View > Preferences, enable 'Show Silkscreen' and 'Show Fab layers'")
print("JLCPCB will read the B.Fab rectangle as the routing/milling boundary.")
