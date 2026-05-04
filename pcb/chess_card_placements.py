#!/usr/bin/env python3
"""
Chess Card PCB v2 — Component Placement + Board Outline Script
==============================================================

Run this INSIDE KiCad's Python scripting console after importing the netlist.

Usage:
  1. Open KiCad PCB editor (Pcbnew) with the chess_card project loaded
  2. Import the netlist: File > Import Netlist > chess_card.net
  3. Tools > Scripting Console
  4. Run:
       exec(open(r"C:/path/to/chess_card_placements.py").read())
  5. Press F5 to refresh the display

What this script does:
  - Draws the 95x60mm board outline on Edge.Cuts with 2mm corner radius
  - Places all 76 components at exact coordinates relative to board corner
  - Flips back-side components to B.Cu
  - Does NOT route any copper traces (that's your job after this)

BOARD_ORIGIN below is the absolute KiCad coordinate of the top-left
corner of the card. Change it if you want the board somewhere else
on the canvas. Default puts the top-left corner at (100, 100) mm,
which is a safe distance from the KiCad origin.
"""

import pcbnew

BOARD_ORIGIN_X = 100.0   # mm — absolute X of top-left card corner
BOARD_ORIGIN_Y = 100.0   # mm — absolute Y of top-left card corner
BOARD_W = 95.0
BOARD_H = 60.0
CORNER_R = 2.0           # mm — corner radius on Edge.Cuts

# ============================================================================
# PLACEMENTS — (x_mm, y_mm, rotation_deg, layer)
# layer: "F" = front (F.Cu), "B" = back (B.Cu)
# ============================================================================

PLACEMENTS = {

    # ===== FRONT FACE =====

    # Touch pads (right column, vertical)
    "TP1":  (88, 14, 0,   "F"),   # touch UP
    "TP2":  (88, 28, 0,   "F"),   # touch SEL  (RTC wake)
    "TP3":  (88, 42, 0,   "F"),   # touch DN

    # USB-C and ESD protection (right edge bottom corner)
    "J1":   (89, 55, 90,  "F"),   # USB-C, opening facing right edge
    "U6":   (78, 51, 0,   "F"),   # USBLC6 ESD
    "C6":   (72, 51, 0,   "F"),   # 10uF VBUS bulk
    "R3":   (82, 50, 90,  "F"),   # CC1 5.1k pull-down
    "R4":   (82, 53, 90,  "F"),   # CC2 5.1k pull-down

    # FPC connector for e-paper (front, immediately below the panel)
    # The e-paper panel sits at front y=2..42; the FPC tail wraps out the bottom
    "J3":   (10, 47, 0,   "F"),

    # ===== BACK FACE =====

    # ESP32-S3 module + immediate decoupling (upper-left)
    "U1":   (14, 13, 0,   "B"),   # ESP32-S3-WROOM module, antenna up
    "C1":   (25,  4, 0,   "B"),   # 100nF
    "C2":   (25,  8, 0,   "B"),   # 100nF
    "C3":   (25, 12, 0,   "B"),   # 100nF
    "C4":   (25, 16, 0,   "B"),   # 10uF bulk
    "C5":   (29, 10, 0,   "B"),   # 100uF inference bulk (1210)
    "R2":   (29, 14, 0,   "B"),   # EN 10k pull-up
    "TP4":  (29, 22, 0,   "B"),   # RST_A bridge pad
    "TP5":  (32, 22, 0,   "B"),   # RST_B bridge pad

    # Solar cell solder pads (upper-right of back; cell adheres above pads)
    "J4":   (46,  4, 0,   "B"),

    # E-paper bypass + charge pump caps (back, near front-side J3)
    "C18":  (35, 22, 0,   "B"),   # 1uF VDDIO bypass
    "C19":  (38, 22, 0,   "B"),   # 1uF VCI bypass
    "C20":  (41, 22, 0,   "B"),   # 1uF VDD logic
    "C21":  (44, 22, 0,   "B"),   # 1uF VPP
    "C22":  (47, 22, 0,   "B"),   # 1uF VSH-VSL flying (must rewire — see note)
    "C23":  (50, 22, 0,   "B"),   # 1uF VGH-VGL flying (must rewire — see note)
    "C24":  (53, 22, 0,   "B"),   # 1uF VCOM
    "R23":  (35, 25, 0,   "B"),   # E-paper BS 10k tie

    # MCP73832 USB charger (right of LiPo pocket)
    "U2":   (44, 30, 0,   "B"),
    "C7":   (47, 30, 0,   "B"),   # 4.7uF VBUS in
    "C8":   (44, 32.5, 0, "B"),   # 4.7uF VBAT out
    "R1":   (47, 32.5, 0, "B"),   # PROG 2k

    # BQ25570 solar harvester
    "U3":   (53, 30, 0,   "B"),
    "L1":   (53, 27, 0,   "B"),   # 22uH boost inductor
    "C9":   (49, 32.5, 0, "B"),   # 4.7uF VIN_DC
    "C10":  (53, 32.5, 0, "B"),   # 10nF VREF_SAMP
    "C11":  (57, 32.5, 0, "B"),   # 22uF VSTOR
    "C12":  (51, 34.5, 0, "B"),   # 4.7uF VBAT
    "C13":  (55, 34.5, 0, "B"),   # 10uF VOUT

    # XC6220 LDO
    "U4":   (62, 30, 0,   "B"),
    "C14":  (59, 32.5, 0, "B"),   # 1uF VIN
    "C15":  (65, 32.5, 0, "B"),   # 1uF VOUT

    # MAX17048 fuel gauge + I2C pull-ups
    "U5":   (70, 30, 0,   "B"),
    "C16":  (67, 32.5, 0, "B"),   # 1uF VDD
    "C17":  (73, 32.5, 0, "B"),   # 100nF VDD HF
    "R10":  (67, 34.5, 0, "B"),   # I2C SDA pullup 4.7k
    "R11":  (73, 34.5, 0, "B"),   # I2C SCL pullup 4.7k

    # Discrete actives in the power chain
    "Q1":   (78, 30, 0,   "B"),   # 2N7002 haptic gate
    "D1":   (82, 30, 0,   "B"),   # BAT54S OR-ing
    "D2":   (86, 30, 0,   "B"),   # 1N4148W flyback (haptic)

    # Battery + motor connectors (right edge area)
    "J2":   (45, 47, 0,   "B"),   # JST-PH SMD (LiPo connector); just outside pocket
    "J5":   (88, 43, 0,   "B"),   # ERM motor solder pads

    # BQ25570 feedback resistor cluster (between U3 and bottom edge)
    "R12":  (52, 38, 0,   "B"),
    "R13":  (55, 38, 0,   "B"),
    "R14":  (58, 38, 0,   "B"),
    "R15":  (52, 40, 0,   "B"),
    "R16":  (55, 40, 0,   "B"),
    "R17":  (58, 40, 0,   "B"),
    "R18":  (61, 40, 0,   "B"),
    "R19":  (52, 42, 0,   "B"),
    "R20":  (55, 42, 0,   "B"),
    "R21":  (58, 42, 0,   "B"),
    "R22":  (61, 42, 0,   "B"),

    # Charge level LEDs + their current-limit Rs (bottom strip, LED+R interleaved
    # to fit in 3mm strip below LiPo pocket)
    "D3":   ( 7, 58.5, 0, "B"),   "R5":  ( 9, 58.5, 0, "B"),
    "D4":   (13, 58.5, 0, "B"),   "R6":  (15, 58.5, 0, "B"),
    "D5":   (19, 58.5, 0, "B"),   "R7":  (21, 58.5, 0, "B"),
    "D6":   (25, 58.5, 0, "B"),   "R8":  (27, 58.5, 0, "B"),
    "D7":   (31, 58.5, 0, "B"),   "R9":  (33, 58.5, 0, "B"),

    # Debug test points (right of LEDs, in same bottom strip)
    "TP6":  (66, 58.5, 0, "B"),   # UART TX (GPIO43)
    "TP7":  (70, 58.5, 0, "B"),   # UART RX (GPIO44)
    "TP8":  (74, 58.5, 0, "B"),   # 3V3 probe
    "TP9":  (78, 58.5, 0, "B"),   # VBAT probe
}

# ============================================================================
# Apply placements via pcbnew Python API
# ============================================================================

def mm(val):
    """Convert mm to KiCad internal units."""
    return pcbnew.FromMM(val)

def vec(x_mm, y_mm):
    """Absolute board coordinate from card-relative mm position."""
    return pcbnew.VECTOR2I(
        mm(BOARD_ORIGIN_X + x_mm),
        mm(BOARD_ORIGIN_Y + y_mm)
    )

def draw_board_outline(board):
    """Draw rounded-rect board outline on Edge.Cuts."""
    # Remove any existing Edge.Cuts lines to avoid duplicates
    to_remove = [d for d in board.GetDrawings()
                 if d.GetLayer() == pcbnew.Edge_Cuts]
    for d in to_remove:
        board.Remove(d)

    ox, oy = BOARD_ORIGIN_X, BOARD_ORIGIN_Y
    W, H, R = BOARD_W, BOARD_H, CORNER_R

    edge = pcbnew.Edge_Cuts

    def seg(x1, y1, x2, y2):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(edge)
        s.SetWidth(mm(0.05))
        s.SetStart(pcbnew.VECTOR2I(mm(ox+x1), mm(oy+y1)))
        s.SetEnd(  pcbnew.VECTOR2I(mm(ox+x2), mm(oy+y2)))
        board.Add(s)

    def arc(cx, cy, start_angle_deg, end_angle_deg):
        """Arc going from start_angle to end_angle counter-clockwise."""
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetLayer(edge)
        a.SetWidth(mm(0.05))
        # Center
        center = pcbnew.VECTOR2I(mm(ox+cx), mm(oy+cy))
        # Start point (at start_angle)
        import math
        sx = cx + R * math.cos(math.radians(start_angle_deg))
        sy = cy + R * math.sin(math.radians(start_angle_deg))
        start  = pcbnew.VECTOR2I(mm(ox+sx), mm(oy+sy))
        ex = cx + R * math.cos(math.radians(end_angle_deg))
        ey = cy + R * math.sin(math.radians(end_angle_deg))
        end    = pcbnew.VECTOR2I(mm(ox+ex), mm(oy+ey))
        a.SetCenter(center)
        a.SetStart(start)
        a.SetEnd(end)
        board.Add(a)

    # Straight segments (inset by R at corners)
    seg(R, 0,   W-R, 0)        # top
    seg(W, R,   W,   H-R)      # right
    seg(W-R, H, R,   H)        # bottom
    seg(0,   H-R, 0, R)        # left

    # Corner arcs
    arc(R,   R,   180, 270)    # top-left
    arc(W-R, R,   270, 360)    # top-right
    arc(W-R, H-R,   0,  90)    # bottom-right
    arc(R,   H-R,  90, 180)    # bottom-left

    print("Board outline drawn on Edge.Cuts (95x60mm, r=2mm corners).")


def apply_to_board():
    board = pcbnew.GetBoard()
    if not board:
        print("ERROR: No board loaded. Open a .kicad_pcb file first.")
        return

    # Step 1: draw board outline
    draw_board_outline(board)

    # Step 2: place all components
    placed, skipped, missing = 0, [], []
    fp_map = {fp.GetReference(): fp for fp in board.GetFootprints()}

    for ref, (x, y, rot, layer) in PLACEMENTS.items():
        fp = fp_map.get(ref)
        if not fp:
            missing.append(ref)
            continue

        # Absolute position
        fp.SetPosition(vec(x, y))

        # Rotation — KiCad stores in tenths of a degree internally,
        # but SetOrientationDegrees takes degrees directly in v7+
        try:
            fp.SetOrientationDegrees(rot)
        except AttributeError:
            fp.SetOrientation(rot * 10)   # fallback for older API

        # Layer flip
        target = pcbnew.B_Cu if layer == "B" else pcbnew.F_Cu
        if fp.GetLayer() != target:
            fp.Flip(fp.GetPosition(), False)

        placed += 1

    # Report
    print(f"\nPlaced {placed}/{len(PLACEMENTS)} components.")
    if skipped:
        print(f"Skipped: {skipped}")
    if missing:
        print(f"Not found on board (check netlist import): {missing}")

    pcbnew.Refresh()
    print("\nDone. Board origin: ({ox}, {oy}) mm. "
          "Use Edit > Set User Grid Origin to snap to card corner if needed.".format(
          ox=BOARD_ORIGIN_X, oy=BOARD_ORIGIN_Y))
    print("Next steps:")
    print("  1. Press F5 to refresh")
    print("  2. Press Ctrl+A to select all, then fit to screen")
    print("  3. Manually add antenna keepout zone above U1")
    print("  4. Route copper (or run Freerouting autorouter)")


apply_to_board()
