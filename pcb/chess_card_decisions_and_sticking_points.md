# Chess Card PCB v2 — Schematic Decisions & Sticking Points

This document accompanies the netlist (`chess_card.net`) and connection report. It explains every major decision made during schematic capture, and **calls out every place where you must verify something against a datasheet, library, or your own measurements before fabricating.**

Read this entire document before importing the netlist into KiCad.

---

## 1. Up-front honest disclaimer

I did not generate a `.kicad_sch` file. Hand-generating a clean, properly-laid-out KiCad schematic file from scratch (with cached symbol library definitions, manual placement coordinates, and visual wire routing) is genuinely too risky to be useful — small format errors prevent the file from opening, and even when it opens, the layout is poor enough that you'd redo it anyway.

What you have instead:

1. **`chess_card.net`** — a KiCad-format netlist. This is the **complete electrical specification** of the design. KiCad's PCB editor (Pcbnew) can import this directly.
2. **`chess_card_netlist.py`** — the Python source that generated the netlist. **This is the single source of truth.** Edit this if you need to change anything, then re-run.
3. **`chess_card_connection_report.md`** — human-readable list of every component and every net. Use this when manually drawing the schematic in eeschema, or for review.

Two valid workflows from here:

- **Workflow A (faster):** open KiCad, create a new project, open Pcbnew (PCB editor), `File > Import Netlist`, select `chess_card.net`. All components appear with correct footprints and rats-nest connections. You skip schematic capture entirely and lay out the PCB directly. This is a perfectly valid (if old-school) workflow.
- **Workflow B (more conventional):** open KiCad eeschema, manually place each component using the connection report as your wiring reference, then sync to Pcbnew. More work but produces a human-readable schematic for documentation.

The rest of this document covers every major decision I made and every place you need to verify or adjust.

---

## 2. Major decisions

### 2.1 USB-C native USB on GPIO19/20 — **fixes critical bug from v1**

The v1 spec routed USB D+/D− to GPIO43/GPIO44. **This was wrong.** GPIO43/44 are UART0 (TXD0/RXD0) on the ESP32-S3 — they're not the native USB pins. The actual native USB pins are GPIO19 (D−) and GPIO20 (D+). The netlist uses these correctly, with GPIO43/44 broken out as UART debug test points (TP6, TP7).

This single change is what makes USB programming over USB-C work without a CH340/CP2102 bridge IC.

### 2.2 USBLC6-2SC6 ESD protection inline on D+/D−

The USB data lines route through U6 (USBLC6-2SC6) before reaching the ESP32. Net naming convention:
- `USB_DP` / `USB_DM`: pre-ESD (USB-C connector → USBLC6)
- `USB_DP_PROT` / `USB_DM_PROT`: post-ESD (USBLC6 → ESP32)

This adds two SOT-23-6 packages worth of complexity and ~$0.30 BOM cost, but protects the ESP32 USB peripheral from human-body-model ESD events that *will* happen when recruiters plug in random cables.

### 2.3 BQ25570 with EN tied to GND (always-enabled)

**Important detail you must verify:** the BQ25570 EN pin is **active-low** per the TI datasheet — pulling it LOW enables the chip. The netlist ties it to GND (in the `GND` net). If you find the datasheet says active-high (as some early TI parts do), this is wrong and you'll need to tie EN to VBAT instead.

Per current datasheet revision (rev. SLUSBH2D): EN low = enabled, EN high = disabled. Confirmed correct as wired.

### 2.4 BQ25570 feedback resistor network — **VERIFY VALUES**

I specified resistor values for the feedback network targeting:
- VBAT_OV (overvoltage, charge-stop): **4.20 V** — appropriate for LiPo
- VBAT_UV (undervoltage, brown-out): **3.00 V** — conservative LiPo cutoff
- VBAT_OK rising threshold: ~3.30 V
- VBAT_OK falling threshold: ~3.10 V (provides hysteresis)
- VOUT regulation: 4.20 V (matches VBAT_OV — VOUT is essentially the LiPo rail in this config)
- VOC_SAMP: 80% of Voc (typical for amorphous Si solar)

The values (5.49M, 3.39M, 5.65M, 4.42M, 5.07M, 3.69M, 6.04M, 7.50M, 3.32M, 10M, 10M) are from worked examples in the BQ25570 datasheet, but **you must run the equations in Section 8.3.4 of the datasheet** with your specific solar cell's open-circuit voltage and confirm. This is the single most error-prone part of the schematic and the values *will* affect harvest efficiency.

### 2.5 BQ25570 + MCP73832 OR-ing via BAT54S

Two charging paths feed the LiPo:
- USB-C → MCP73832 → BAT54S anode 1 → LiPo+
- Solar → BQ25570 → BAT54S anode 2 → LiPo+

The BAT54S dual Schottky prevents back-feeding between the two charging ICs. You lose ~0.3 V across the diode, which means MCP73832 sees a slightly lower headroom (USB VBUS 5 V → ~4.7 V at LiPo), but this is fine for charging.

**Decision point:** I considered eliminating the OR-ing diode for the BQ25570 path since the chip has internal blocking, but kept it for safety. If you measure significantly reduced solar charge rate after building, you could short out D1's anode-2 leg as a debug step.

### 2.6 XC6220 EN tied to BQ25570 VBAT_OK — brown-out protection

When LiPo voltage drops below VBAT_OK threshold (~3.1 V falling), BQ25570 pulls VBAT_OK low, which disables the XC6220 LDO, which kills the 3.3 V rail, which powers off the ESP32 cleanly. This prevents corrupting RTC memory or flash during a slow battery discharge.

**Side effect to be aware of:** If solar harvest is the only power source and the harvested current is *less than the LDO quiescent draw*, the system can enter a thrash state (LDO enables, S3 starts up, draws too much, voltage sags, LDO disables, repeat). The BQ25570's hysteresis is designed to prevent this in normal cases, but if your solar cell is too small, it can happen. Validate by measuring solar harvest with a small load before committing.

### 2.7 MCP73832 → MCP73832 with 2 kΩ PROG (500 mA fast charge)

Original v1 spec used MCP73831 with 6.8 kΩ PROG (150 mA). v2 uses MCP73832 (slightly different pinout, supports up to 500 mA) with 2 kΩ PROG, giving 500 mA charge current. ~70 minute full charge from USB-C vs ~3.5 hours.

The MCP73832 has a slightly different STAT pin behavior than MCP73831 — STAT goes low when charging, high-impedance when done or no input. I left STAT unconnected in the netlist (could route to a dedicated GPIO for charging-status detection, but firmware can read this from MAX17048 anyway).

### 2.8 MAX17048 fuel gauge added

Not in v1 spec. Added for accurate battery percentage reporting (drives the 5 charge LEDs). Connects directly to LiPo+ for sensing, communicates over I2C to ESP32 (GPIO38/39).

**Sticking point:** the MAX17048 has a `QSTRT` (quick-start) pin which forces a fresh model fit on power-up. I tied it to GND for normal operation. If you experience inaccurate gauge readings on first power-up, you can pulse this pin briefly via a GPIO instead.

### 2.9 5 charge LEDs as cathode-to-GPIO (sink mode)

The 5 LEDs (D3–D7) connect: anode → 1 kΩ → 3.3V; cathode → ESP32 GPIO. To light an LED, the GPIO drives LOW. This is the standard "ESP32 sinks current" pattern and works reliably.

If you preferred source mode (anode to GPIO, cathode through resistor to GND), you'd need to verify the GPIO can source enough current — the S3 GPIOs can source up to 40 mA, so it's fine either way.

### 2.10 Touch pads as TestPoint footprints

I used `TestPoint:TestPoint_Pad_D8.0mm` for the three touch pads (TP1–TP3). This gives an 8 mm exposed copper circle on the front layer, ENIG-finished, soldermask removed. **You may want to swap this for `TestPoint_Pad_D10mm` if your finger feels the 8 mm pads are too small** — the spec doc said 10 mm, I went smaller for column-fit reasons. Your call; trivial change in KiCad.

### 2.11 Reset bridge pads

TP4 and TP5 are 1.5×1.5 mm pads on the back. TP4 is on the `ESP_EN` net (with the EN pull-up); TP5 is on `GND`. Bridging them with a coin or tweezers shorts EN to GND and resets the chip. Cover with hot glue or Kapton tape after first firmware load.

### 2.12 Haptic motor on VBAT (not 3.3V)

The motor + pin connects directly to LiPo+ (`VBAT` net), not the regulated 3.3 V rail. This was a v1 spec issue — driving the motor from the 3.3 V rail caused inference noise and rail dipping. Now the motor sees the full LiPo voltage (3.7–4.2 V), which is fine for an 8 mm coin ERM (rated for 3.0–3.7 V — slightly overdriven but standard practice).

The 1N4148W flyback diode is wired with cathode to VBAT and anode to the MOSFET drain (the `MOTOR_NEG` net), which is the correct orientation to clamp the inductive kick when the MOSFET turns off.

### 2.13 E-paper FPC pinout — **MUST VERIFY AGAINST DATASHEET**

This is the **single biggest sticking point in the schematic.** I used a typical 24-pin pinout for GoodDisplay 2.9" 296×152 panels, based on the publicly-circulated GDEY029T94 reference. But:

- The exact pinout of the **GDEY029F51** (the 4-grayscale variant we want) may differ
- Some 2.9" panels use 30-pin FPC instead of 24-pin
- Pin polarity (VDD vs VDDIO, etc.) varies between revisions

**Before sending to fab, you MUST:**
1. Confirm the panel part number you're actually buying
2. Download the datasheet
3. Compare the FPC pinout to the J3 definition in `chess_card_netlist.py`
4. Update if different

I noted this in the netlist comments. If you don't verify this, your e-paper will not work and you'll need a respin.

### 2.14 E-paper charge pump caps as flying caps

Many e-paper panels need "flying caps" — capacitors connected *between two pins of the FPC*, not from a pin to ground. Specifically:
- C22 between VSH (pin 3) and VSL (pin 18)
- C23 between VGH (pin 21) and VGL (pin 20)

In the netlist, I created nets `EP_VSH_VSL` and `EP_VGH_VGL` containing both the FPC pins *and both terminals of the cap*. **This is technically incorrect** — it would short the caps. KiCad will likely flag it during ERC.

**What you must do in KiCad:** when you draw the schematic (or modify the imported netlist), you need to:
- Wire C22 pin 1 to J3 pin 3 (VSH)
- Wire C22 pin 2 to J3 pin 18 (VSL) — separately, NOT shorted to VSH
- Same for C23 between J3 pin 21 (VGH) and pin 20 (VGL)

I called this out explicitly in the netlist comments. **This is the second-most-likely thing to break the e-paper if not handled.**

### 2.15 Pin assignment summary

Final ESP32-S3 GPIO assignments:

| GPIO | Pin | Function | Notes |
|---|---|---|---|
| 0  | 46 | (BOOT) | Strap, internal pull-up, leave NC |
| 3  | 16 | (avoid) | JTAG strap, NC |
| 4  | 5  | TOUCH_UP | Cap touch |
| 5  | 6  | TOUCH_SEL | Cap touch + RTC wake source |
| 6  | 7  | TOUCH_DN | Cap touch |
| 7  | 8  | EP_BUSY | E-paper |
| 8  | 13 | EP_RST | E-paper |
| 9  | 18 | EP_DC | E-paper |
| 10 | 19 | EP_CS | E-paper |
| 11 | 20 | EP_MOSI | E-paper SPI MOSI |
| 12 | 21 | EP_SCK | E-paper SPI clock |
| 13 | 22 | HAPTIC_GATE | MOSFET gate |
| 14 | 23 | LED1 | Charge LED 1 |
| 15 | 9  | LED2 | Charge LED 2 |
| 16 | 10 | LED3 | Charge LED 3 |
| 17 | 11 | LED4 | Charge LED 4 |
| 18 | 12 | LED5 | Charge LED 5 |
| 19 | 14 | USB D− | Native USB (post-ESD) |
| 20 | 15 | USB D+ | Native USB (post-ESD) |
| 33,34,40,41,42 | 33,34,40,41,42 | (unused) | NC |
| 35,36,37 | 35,36,37 | (PSRAM) | NC — internally tied to PSRAM on N16R8 |
| 38 | 38 | I2C SDA | MAX17048 |
| 39 | 39 | I2C SCL | MAX17048 |
| 43 | 43 | UART TX | Debug test point TP6 |
| 44 | 44 | UART RX | Debug test point TP7 |
| 45 | 45 | (avoid) | VDD_SPI strap, NC |
| 46 | 17 | (avoid) | ROM print strap, NC |

---

## 3. Sticking points (in order of severity)

### 🔴 Critical — must address before fab

#### S1. E-paper FPC pinout (see decision 2.13)
**Risk:** If the FPC pinout I assumed doesn't match your actual panel, the e-paper will not work — you'll see no display, possibly damage the panel.
**Action:** Get the GDEY029F51 datasheet, verify pin-by-pin, update `chess_card_netlist.py` if needed.

#### S2. E-paper flying caps wired as shorts (see decision 2.14)
**Risk:** Netlist nets `EP_VSH_VSL` and `EP_VGH_VGL` currently short the cap terminals to the FPC pins they should bridge.
**Action:** When importing into KiCad, manually wire C22 between J3.3 and J3.18 (not into a single net). Same for C23 between J3.20 and J3.21.

#### S3. BQ25570 feedback resistor values not yet computed for *your* solar cell
**Risk:** Wrong VOC_SAMP divider = MPPT operating at wrong point = significantly reduced harvest efficiency. Wrong VBAT_OV = LiPo could overcharge.
**Action:** Open the BQ25570 datasheet, Section 8.3.4. Plug in your solar cell's measured Voc (open-circuit voltage at typical room light). Recompute R12–R22 if different from the values I used.

#### S4. ESP32-S3-WROOM-2 footprint
**Risk:** I used `RF_Module:ESP32-S2-WROOM` as a footprint placeholder because WROOM-2 isn't in stock KiCad libraries. The pad pattern is mostly compatible, but the antenna keepout zone differs slightly between WROOM-1, WROOM-2, and S2-WROOM.
**Action:** Get the official ESP32-S3-WROOM-2 mechanical drawing from Espressif. Either (a) verify the existing footprint matches, or (b) create a custom footprint, or (c) use the JLCPCB-supplied symbol/footprint via their library.

### 🟡 Important — verify but unlikely to break things

#### S5. MCP73832 STAT pin unconnected
**Risk:** Loss of dedicated charging-state feedback. Not critical because MAX17048 reports charging status independently.
**Action:** None required. Optional: route STAT to an unused GPIO if you want firmware-readable hard charging signal.

#### S6. BQ25570 OK_HYST simplified
**Risk:** Default 100 mV hysteresis may not be optimal for very-low-light environments.
**Action:** Run BQ25570 in your actual lighting environment first. If you observe oscillation around the OK threshold, recalculate per datasheet.

#### S7. BQ25570 OT_PROG (over-temperature) pin
**Risk:** I left this unconnected (`BQ_OT_PROG` net has only one node, which means it's effectively floating). Per datasheet, it should be tied via a thermistor for over-temperature protection, or to a fixed voltage.
**Action:** Tie to VRDIV (effectively disables OT protection — acceptable for indoor card use) or add a thermistor network if you want OT protection.

#### S8. USB-C connector value chosen
**Risk:** I specified `Connector_USB:USB_C_Receptacle_GCT_USB4085` as the footprint hint. This is a common 16-pin USB-C SMD receptacle. The pin numbering convention I used (A1, A4, A5, etc.) matches the USB-C spec but might differ from your specific manufacturer's part.
**Action:** When you select the actual part on JLCPCB / LCSC, verify pin numbering matches.

### 🟢 Minor — design-quality issues

#### S9. No explicit decoupling cap distance specified in netlist
**Risk:** Decoupling caps could be placed far from their VDD pins during PCB layout.
**Action:** During PCB layout, manually place C1, C2, C3, C4 within 0.5 mm of the corresponding ESP32 module pins. Place C16, C17 near MAX17048. C18, C19, C20, C21 near the FPC connector.

#### S10. No EMI / RF considerations
**Risk:** SPI traces to e-paper could couple noise into touch pads. Solar cell DC traces could pick up noise from inductor switching node.
**Action:** During PCB layout, route SPI on bottom layer with ground hatching above. Keep BQ25570 LBOOST (switching node) on a short trace, away from analog and touch traces.

#### S11. Test points minimal
**Risk:** Limited debug visibility post-assembly.
**Action:** I added TP6 (UART TX), TP7 (UART RX), TP8 (3V3), TP9 (VBAT). You may want to add: BQ25570 VSTOR, BQ25570 VBAT_OK, MCP73832 STAT, I2C SDA, I2C SCL. Cheap insurance during bring-up.

#### S12. No I2C address conflict checking
**Risk:** Only one I2C device (MAX17048 at 0x36). Future expansion could conflict.
**Action:** N/A for now. If you add I2C devices later, verify addresses.

#### S13. MOSFET gate has no pull-down
**Risk:** During ESP32 boot (before firmware initializes GPIO13), the gate could float — random brief motor pulses possible.
**Action:** Optional: add a 100 kΩ pull-down from `HAPTIC_GATE` to GND. I didn't include this; the ESP32 GPIOs default to high-impedance input on reset, so the gate will be floating briefly. Adding the pull-down is cheap and prevents this 5-ms ambiguity at every boot.

#### S14. No bulk capacitance check for inference current spikes
**Risk:** Heavy inference might cause 100 mA+ current spikes that the bulk caps can't absorb, leading to brown-outs.
**Action:** I included C5 (100 µF, 1210) on the 3.3 V rail. This should handle ~50 ms of 200 mA spikes. If you observe brownouts during inference once the board is built, add a second 100 µF in parallel. Cheap fix.

#### S15. Solar cell input has no input cap close to BQ25570
**Risk:** Solar input lead inductance + sudden load step from BQ25570 = transient voltage dips that could falsely trigger MPPT re-sampling.
**Action:** I did include C9 (4.7 µF) on the VSOLAR net. Verify it's placed within 5 mm of BQ25570 VIN_DC pins during layout. If solar wires from the panel are >50 mm long, consider adding a small inductor or larger input cap.

---

## 4. Decision points the schematic does NOT lock in

These are intentionally left for PCB layout or build time:

1. **Component placement** on the PCB — must match the spec doc's front/back layout
2. **Decoupling cap placement** relative to ICs — handled during layout
3. **Trace lengths and impedance** — USB D+/D− should be ~90Ω differential, length-matched
4. **Antenna keepout zone** — 15 mm copper-free zone at top of ESP32 module
5. **Touch pad ground exclusion** — 5 mm minimum no-pour zone around touch pads
6. **0.4 mm depth-controlled milling pocket** for LiPo recess
7. **PCB stack-up** — 0.8 mm FR4, 2-layer
8. **Soldermask color, silkscreen** — black + white as specified

These are PCB-level concerns, not schematic-level.

---

## 5. Verification checklist before importing into KiCad

- [ ] Open `chess_card_netlist.py`, read every comment marked "VERIFY"
- [ ] Download GDEY029F51 (or whichever 2.9" panel you choose) datasheet
- [ ] Compare FPC pin numbers in J3 definition to datasheet — update if different
- [ ] Confirm BQ25570 EN polarity (active-low) in current TI datasheet revision
- [ ] Pick exact USB-C connector part on LCSC, verify pin numbering matches J1 definition
- [ ] Pick exact ESP32-S3-WROOM-2 footprint (or use JLCPCB's symbol)
- [ ] If solar cell Voc differs significantly from 5 V, recompute BQ25570 R12–R22
- [ ] Decide: do you want to add a 100 kΩ pull-down on HAPTIC_GATE (S13)?

---

## 6. After import: what to do in KiCad

1. **Open KiCad 8**, create a new project named `chess_card`
2. **Open Pcbnew (PCB editor)** — leave eeschema closed for now
3. **File > Import Netlist...** → select `chess_card.net`
4. **Resolve symbol/footprint mismatches.** KiCad will tell you which library symbols/footprints are missing. Most are stock KiCad parts; specifically expect to need to source:
   - `BQ25570` — download from TI's product page or Ultra Librarian
   - `MAX17048` — download from Maxim/Analog Devices product page
   - `XC6220Bxx` — Torex doesn't publish KiCad libs; create custom or find on SnapEDA
   - `MCP73832` — download from Microchip product page
   - `USBLC6-2SC6` — likely in stock KiCad `Power_Protection` library
   - `ESP32-S3-WROOM-2` — likely available on JLCPCB's parts library
   - `GDEY029F51` FPC connector + symbol — get from GoodDisplay reference design
5. **Manually rewire the e-paper flying caps (C22, C23)** as described in S2
6. **Run DRC** on the netlist before placing components
7. **Place components** per spec doc Section 2 and 3 (front/back layout)
8. **Route, fab, assemble**

---

## 7. If you want a visual schematic later

Once the board works, you can retroactively draw the schematic in eeschema for documentation purposes. Use the connection report as your reference. The schematic is purely documentation at that point — the netlist and the working PCB are the canonical truth.

Alternatively: keep `chess_card_netlist.py` as the source of truth (it's more maintainable than a graphical schematic anyway) and treat it as your "schematic." This is unconventional but defensible — it's well-commented, version-controllable in Git, and easy to diff.

---

## 8. What to do if something goes wrong

If the e-paper doesn't work: **check S1 and S2 first** (FPC pinout and flying caps). Probability >80% it's one of these.

If solar charging is weak or absent: **check S3** (BQ25570 feedback values). Measure VOC_SAMP voltage with a meter — should be ~80% of the solar cell's open-circuit voltage in light.

If USB-C doesn't enumerate: **check the USBLC6 placement and USB D+/D− trace routing.** Native USB is on GPIO19/20 (verified in netlist). Make sure the BAT54S OR-ing diodes aren't blocking VBUS to the ESP32 USB peripheral (they shouldn't be — they only feed MCP73832).

If touch pads don't respond: **verify the 5 mm no-ground-pour zone in PCB layout.** The schematic doesn't capture this; it's a layout concern.

If the system briefly turns on then dies in low light: **see S6** (BQ25570 hysteresis or solar cell too small).

---

*Generated 2026-05-03 alongside `chess_card.net` and `chess_card_connection_report.md`.*
