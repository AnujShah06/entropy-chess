"""
Chess Card — DRC Fix (standalone version)
==========================================
Run this from a command line, NOT inside KiCad's scripting console:
  
  Open KiCad's "KiCad Command Prompt" (Start menu > KiCad > KiCad Command Prompt)
  cd to your project directory:
    cd C:/Users/rneel/Neelay/Code/entropy-chess/pcb
  Run:
    python fix_drc_standalone.py chess_PCB.kicad_pcb

  IMPORTANT: Close the .kicad_pcb file in KiCad first (File > Close), or save
  your work, because this script writes back to the same file.

Why standalone? Running inside KiCad's scripting console has SwigPyObject
wrapping bugs in KiCad 8+. Loading the board from disk via pcbnew.LoadBoard()
returns proper FOOTPRINT objects without needing casts.
"""

import sys
import os

try:
    import pcbnew
except ImportError:
    print("ERROR: pcbnew module not found.")
    print("Make sure you're running this from KiCad's command prompt, not")
    print("a regular Python install. The module ships with KiCad.")
    sys.exit(1)


BOARD_ORIGIN_X = 100.0
BOARD_ORIGIN_Y = 100.0
BOARD_W = 95.0
BOARD_H = 60.0
CHAMFER = 2.0


NEW_POSITIONS = {
    "C1":  (26, 4,    0, "B"),
    "C2":  (26, 8,    0, "B"),
    "C3":  (26, 12,   0, "B"),
    "C4":  (26, 16,   0, "B"),
    "C5":  (30, 10,   0, "B"),
    "R2":  (30, 14,   0, "B"),
    "U2":  (44, 30,   0, "B"),
    "C7":  (48, 30,   0, "B"),
    "C8":  (44, 33,   0, "B"),
    "R1":  (47, 33.5, 0, "B"),
    "U3":  (54, 30,   0, "B"),
    "L1":  (54, 26.5, 0, "B"),
    "C9":  (50, 33,   0, "B"),
    "C10": (54, 33,   0, "B"),
    "C11": (58, 33,   0, "B"),
    "C12": (51, 35.5, 0, "B"),
    "C13": (56, 35.5, 0, "B"),
    "U4":  (64, 30,   0, "B"),
    "C14": (61, 33,   0, "B"),
    "C15": (67, 33,   0, "B"),
    "U5":  (73, 30,   0, "B"),
    "C16": (70, 33,   0, "B"),
    "C17": (76, 33,   0, "B"),
    "R10": (70, 35,   0, "B"),
    "R11": (76, 35,   0, "B"),
    "Q1":  (80, 30,   0, "B"),
    "D1":  (84, 30,   0, "B"),
    "D2":  (88, 33,   0, "B"),
    "R12": (50, 39,   0, "B"),
    "R13": (53, 39,   0, "B"),
    "R14": (56, 39,   0, "B"),
    "R15": (50, 41,   0, "B"),
    "R16": (53, 41,   0, "B"),
    "R17": (56, 41,   0, "B"),
    "R18": (59, 41,   0, "B"),
    "R19": (50, 43,   0, "B"),
    "R20": (53, 43,   0, "B"),
    "R21": (56, 43,   0, "B"),
    "R22": (59, 43,   0, "B"),
}


def mm(v):
    return pcbnew.FromMM(v)


def avec(rx, ry):
    return pcbnew.VECTOR2I(mm(BOARD_ORIGIN_X + rx),
                           mm(BOARD_ORIGIN_Y + ry))


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_drc_standalone.py <path_to_kicad_pcb>")
        sys.exit(1)

    pcb_path = sys.argv[1]
    if not os.path.exists(pcb_path):
        print("ERROR: file not found: " + pcb_path)
        sys.exit(1)

    print("Loading: " + pcb_path)
    board = pcbnew.LoadBoard(pcb_path)
    if board is None:
        print("ERROR: failed to load board")
        sys.exit(1)

    # Backup before modifying
    backup_path = pcb_path + ".bak"
    print("Saving backup to: " + backup_path)
    import shutil
    shutil.copyfile(pcb_path, backup_path)

    # Step 1: redraw board outline
    print("\nStep 1: Redrawing board outline...")
    removed = 0
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(d)
            removed += 1
    print("  Removed " + str(removed) + " old outline shapes")

    W, H, C = BOARD_W, BOARD_H, CHAMFER
    points = [
        (C,    0),    (W-C,  0),
        (W,    C),    (W,    H-C),
        (W-C,  H),    (C,    H),
        (0,    H-C),  (0,    C),
    ]

    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.05))
        s.SetStart(avec(x1, y1))
        s.SetEnd(avec(x2, y2))
        board.Add(s)
    print("  Drew chamfered outline (95x60mm, 2mm chamfer)")

    # Save
    print("\nSaving back to: " + pcb_path)
    pcbnew.SaveBoard(pcb_path, board)

    print("\n" + "="*65)
    print("DONE. Re-open the file in KiCad and:")
    print("="*65)
    print("\n1. File > Board Setup > Design Rules > Constraints:")
    print("     Set 'Minimum hole size' to 0.2mm")
    print("\n2. File > Board Setup > Design Rules > Violation Severity:")
    print("     Change 'Courtyards overlap' to Warning")
    print("     Change 'Silk overlaps board edge' to Warning")
    print("\n3. Re-run DRC.")
    print("\nIf something looks wrong, restore the backup:")
    print("  " + backup_path)


if __name__ == "__main__":
    main()
