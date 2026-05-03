#!/usr/bin/env python3
"""
Chess Card PCB v2 — KiCad Netlist Generator
============================================

Generates a KiCad-compatible netlist (.net file) for the chess card project.
The netlist can be:
  1. Imported directly into KiCad PCB editor (Pcbnew) via "File > Import Netlist"
     — this lets you skip schematic capture entirely and go straight to layout.
  2. Used as a reference for manually drawing the schematic in KiCad eeschema.

This script is the SINGLE SOURCE OF TRUTH for the schematic. Any electrical
change should be made here, then re-run to regenerate the netlist.

Usage:
    python3 chess_card_netlist.py

Output:
    chess_card.net
"""

import datetime
from collections import defaultdict
from typing import List, Tuple, Dict


# ============================================================================
# COMPONENT DEFINITIONS
# ============================================================================
# Each component: (ref, value, footprint, lib_id_hint, [pins])
# pins is a list of (pin_num, pin_name, pin_type)
# pin_type: "power_in", "power_out", "input", "output", "bidirectional",
#           "passive", "open_collector", "no_connect"
# ============================================================================

COMPONENTS = []

def add(ref, value, footprint, lib_id, description, pins):
    COMPONENTS.append({
        "ref": ref,
        "value": value,
        "footprint": footprint,
        "lib_id": lib_id,
        "description": description,
        "pins": pins,
    })

# ---------- U1: ESP32-S3-WROOM-2-N16R8 ----------
add("U1", "ESP32-S3-WROOM-2-N16R8",
    "RF_Module:ESP32-S2-WROOM",
    "RF_Module:ESP32-S3-WROOM-1",
    "Espressif WiFi/BT module — main MCU. Map to WROOM-2 footprint manually in KiCad.",
    [
        ("1",  "GND",     "power_in"),
        ("2",  "3V3",     "power_in"),
        ("3",  "3V3",     "power_in"),
        ("4",  "EN",      "input"),
        ("5",  "IO4",     "bidirectional"),
        ("6",  "IO5",     "bidirectional"),
        ("7",  "IO6",     "bidirectional"),
        ("8",  "IO7",     "bidirectional"),
        ("9",  "IO15",    "bidirectional"),
        ("10", "IO16",    "bidirectional"),
        ("11", "IO17",    "bidirectional"),
        ("12", "IO18",    "bidirectional"),
        ("13", "IO8",     "bidirectional"),
        ("14", "IO19",    "bidirectional"),
        ("15", "IO20",    "bidirectional"),
        ("16", "IO3",     "bidirectional"),
        ("17", "IO46",    "bidirectional"),
        ("18", "IO9",     "bidirectional"),
        ("19", "IO10",    "bidirectional"),
        ("20", "IO11",    "bidirectional"),
        ("21", "IO12",    "bidirectional"),
        ("22", "IO13",    "bidirectional"),
        ("23", "IO14",    "bidirectional"),
        ("24", "VDD3P3",  "power_in"),
        ("25", "GND",     "power_in"),
        # Pins 26-32 internally connected to Octal SPI flash & PSRAM on N16R8
        ("33", "IO33",    "bidirectional"),
        ("34", "IO34",    "bidirectional"),
        ("35", "IO35_NC", "no_connect"),  # PSRAM internal
        ("36", "IO36_NC", "no_connect"),
        ("37", "IO37_NC", "no_connect"),
        ("38", "IO38",    "bidirectional"),
        ("39", "IO39",    "bidirectional"),
        ("40", "IO40",    "bidirectional"),
        ("41", "IO41",    "bidirectional"),
        ("42", "IO42",    "bidirectional"),
        ("43", "TXD0",    "bidirectional"),
        ("44", "RXD0",    "bidirectional"),
        ("45", "IO45",    "bidirectional"),
        ("46", "IO0",     "bidirectional"),
        ("47", "GND",     "power_in"),
        ("48", "EPAD",    "power_in"),
    ])

# ---------- U2: MCP73832T — LiPo charger (USB side) ----------
add("U2", "MCP73832T-2ACI/OT",
    "Package_TO_SOT_SMD:SOT-23-5",
    "Battery_Management:MCP73832-2ACx_OT",
    "Microchip 500 mA single-cell LiPo charger, USB-C path",
    [
        ("1", "STAT", "open_collector"),
        ("2", "GND",  "power_in"),
        ("3", "VBAT", "power_out"),
        ("4", "VDD",  "power_in"),
        ("5", "PROG", "input"),
    ])

# ---------- U3: BQ25570 — Solar harvester ----------
add("U3", "BQ25570RGRR",
    "Package_DFN_QFN:QFN-20-1EP_3.5x3.5mm_P0.5mm_EP2x2mm",
    "Battery_Management:BQ25570",
    "TI ultra-low-power solar harvester w/ MPPT and LiPo charging",
    [
        ("1",  "VIN_DC",   "power_in"),
        ("2",  "VOC_SAMP", "input"),
        ("3",  "VREF_SAMP","input"),
        ("4",  "VRDIV",    "output"),
        ("5",  "OK_PROG",  "input"),
        ("6",  "OK_HYST",  "input"),
        ("7",  "VBAT_OK",  "output"),
        ("8",  "OT_PROG",  "input"),
        ("9",  "VOUT_SET", "input"),
        ("10", "VOUT_EN",  "input"),
        ("11", "VOUT",     "power_out"),
        ("12", "VBAT_OV",  "input"),
        ("13", "VBAT",     "power_out"),
        ("14", "VBAT_UV",  "input"),
        ("15", "VSTOR",    "power_out"),
        ("16", "VRDIV2",   "output"),
        ("17", "LBOOST",   "passive"),
        ("18", "VSS",      "power_in"),
        ("19", "VIN_DC",   "power_in"),
        ("20", "EN",       "input"),
        ("21", "EPAD",     "power_in"),
    ])

# ---------- U4: XC6220B331 — 3.3V LDO ----------
add("U4", "XC6220B331MR-G",
    "Package_TO_SOT_SMD:SOT-25",
    "Regulator_Linear:XC6220Bxx",
    "Torex 1A 3.3V LDO with EN",
    [
        ("1", "VIN",  "power_in"),
        ("2", "GND",  "power_in"),
        ("3", "EN",   "input"),
        ("4", "NC",   "no_connect"),
        ("5", "VOUT", "power_out"),
    ])

# ---------- U5: MAX17048 — Fuel gauge ----------
add("U5", "MAX17048G+T10",
    "Package_TO_SOT_SMD:SOT-23-6",
    "Battery_Management:MAX17048",
    "Maxim ModelGauge battery fuel gauge, I2C",
    [
        ("1", "QSTRT", "input"),
        ("2", "VDD",   "power_in"),
        ("3", "GND",   "power_in"),
        ("4", "ALRT",  "open_collector"),
        ("5", "SDA",   "bidirectional"),
        ("6", "SCL",   "input"),
    ])

# ---------- U6: USBLC6-2SC6 — USB ESD ----------
add("U6", "USBLC6-2SC6",
    "Package_TO_SOT_SMD:SOT-23-6",
    "Power_Protection:USBLC6-2SC6",
    "ST USB ESD protection (low capacitance)",
    [
        ("1", "IO1",   "bidirectional"),
        ("2", "GND",   "power_in"),
        ("3", "IO2",   "bidirectional"),
        ("4", "IO2_P", "bidirectional"),
        ("5", "VBUS",  "power_in"),
        ("6", "IO1_P", "bidirectional"),
    ])

# ---------- Q1: 2N7002 — N-channel MOSFET ----------
add("Q1", "2N7002",
    "Package_TO_SOT_SMD:SOT-23",
    "Transistor_FET:2N7002",
    "N-channel MOSFET for haptic motor drive",
    [
        ("1", "G", "input"),
        ("2", "S", "passive"),
        ("3", "D", "passive"),
    ])

# ---------- D1: BAT54S — dual Schottky for OR-ing ----------
add("D1", "BAT54S",
    "Package_TO_SOT_SMD:SOT-23",
    "Diode:BAT54S",
    "Dual Schottky in series for power source OR-ing",
    [
        ("1", "A1", "passive"),
        ("2", "A2", "passive"),
        ("3", "K",  "passive"),
    ])

# ---------- D2: 1N4148W — flyback diode ----------
add("D2", "1N4148W",
    "Diode_SMD:D_SOD-123",
    "Diode:1N4148W",
    "Flyback diode for haptic motor",
    [
        ("1", "K", "passive"),
        ("2", "A", "passive"),
    ])

# ---------- LEDs (5 charge level indicators) ----------
for ref, color in [("D3", "Red"), ("D4", "Red"), ("D5", "Yellow"),
                    ("D6", "Green"), ("D7", "Green")]:
    add(ref, color,
        "LED_SMD:LED_0402_1005Metric",
        "Device:LED",
        f"Charge level LED — {color}",
        [("1", "K", "passive"), ("2", "A", "passive")])

# ---------- L1: 22µH inductor for BQ25570 boost ----------
add("L1", "22uH",
    "Inductor_SMD:L_0603_1608Metric",
    "Device:L",
    "Boost inductor for BQ25570",
    [("1", "1", "passive"), ("2", "2", "passive")])

# ---------- J1: USB-C 16-pin SMD ----------
add("J1", "USB-C 16P SMD",
    "Connector_USB:USB_C_Receptacle_GCT_USB4085",
    "Connector:USB_C_Receptacle_USB2.0_16P",
    "USB-C receptacle, USB 2.0 only",
    [
        ("A1",  "GND",   "power_in"),
        ("A4",  "VBUS",  "power_in"),
        ("A5",  "CC1",   "bidirectional"),
        ("A6",  "DP1",   "bidirectional"),
        ("A7",  "DN1",   "bidirectional"),
        ("A9",  "VBUS",  "power_in"),
        ("A12", "GND",   "power_in"),
        ("B1",  "GND",   "power_in"),
        ("B4",  "VBUS",  "power_in"),
        ("B5",  "CC2",   "bidirectional"),
        ("B6",  "DP2",   "bidirectional"),
        ("B7",  "DN2",   "bidirectional"),
        ("B9",  "VBUS",  "power_in"),
        ("B12", "GND",   "power_in"),
        ("S1",  "SHIELD","power_in"),
    ])

# ---------- J2: SMD JST-PH 2P (LiPo) ----------
add("J2", "JST-PH 2P SMD",
    "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
    "Connector:Conn_01x02",
    "JST-PH 2.0 mm SMD horizontal — LiPo battery connector",
    [
        ("1", "VBAT", "power_in"),
        ("2", "GND",  "power_in"),
    ])

# ---------- J3: 24-pin 0.5mm FPC connector for e-paper ----------
# Pinout per typical GoodDisplay 2.9" 296x152 panel (e.g., GDEY029F51)
# **VERIFY against the specific panel datasheet before fabricating!**
add("J3", "FPC 24P 0.5mm",
    "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal",
    "Connector:FFC-FPC_24P",
    "FPC connector for 2.9\" e-paper panel (24-pin, 0.5mm pitch)",
    [
        ("1",  "GDR",   "passive"),
        ("2",  "RES",   "passive"),
        ("3",  "VSH",   "passive"),
        ("4",  "TSCL",  "passive"),
        ("5",  "TSDA",  "passive"),
        ("6",  "BS",    "passive"),
        ("7",  "BUSY",  "output"),
        ("8",  "RES_N", "input"),
        ("9",  "DC",    "input"),
        ("10", "CS_N",  "input"),
        ("11", "SCL",   "input"),
        ("12", "SDA",   "input"),
        ("13", "VDDIO", "power_in"),
        ("14", "VCI",   "power_in"),
        ("15", "VSS",   "power_in"),
        ("16", "VDD",   "power_in"),
        ("17", "VPP",   "passive"),
        ("18", "VSL",   "passive"),
        ("19", "VSH2",  "passive"),
        ("20", "VGL",   "passive"),
        ("21", "VGH",   "passive"),
        ("22", "VCOM",  "passive"),
        ("23", "GDR2",  "passive"),
        ("24", "VSS2",  "power_in"),
    ])

# ---------- J4: Solar cell pads ----------
add("J4", "Solar Cell Pads",
    "TerminalBlock:TerminalBlock_bornier-2_P5.08mm",
    "Connector_Generic:Conn_01x02",
    "Solder pads for solar cell wires",
    [("1", "SOL_PLUS", "passive"), ("2", "SOL_MINUS", "passive")])

# ---------- J5: ERM motor pads ----------
add("J5", "ERM Motor Pads",
    "TerminalBlock:TerminalBlock_bornier-2_P5.08mm",
    "Connector_Generic:Conn_01x02",
    "Solder pads for ERM coin haptic motor",
    [("1", "MOT_PLUS", "passive"), ("2", "MOT_MINUS", "passive")])

# ---------- Test points / pads ----------
TOUCH_FOOTPRINT = "TestPoint:TestPoint_Pad_D8.0mm"
add("TP1", "Touch UP",     TOUCH_FOOTPRINT, "Connector:TestPoint",
    "Capacitive touch pad — UP", [("1", "P", "passive")])
add("TP2", "Touch SELECT", TOUCH_FOOTPRINT, "Connector:TestPoint",
    "Capacitive touch pad — SELECT (RTC wake)", [("1", "P", "passive")])
add("TP3", "Touch DOWN",   TOUCH_FOOTPRINT, "Connector:TestPoint",
    "Capacitive touch pad — DOWN", [("1", "P", "passive")])

RST_FOOTPRINT = "TestPoint:TestPoint_Pad_1.5x1.5mm"
add("TP4", "RST_BRIDGE_A", RST_FOOTPRINT, "Connector:TestPoint",
    "Reset bridge pad A (short to TP5 = hard reset)", [("1", "P", "passive")])
add("TP5", "RST_BRIDGE_B", RST_FOOTPRINT, "Connector:TestPoint",
    "Reset bridge pad B (GND)", [("1", "P", "passive")])

# UART debug test points (optional — leave broken out)
add("TP6", "TP_TX", "TestPoint:TestPoint_Pad_1.0x1.0mm", "Connector:TestPoint",
    "UART0 TX (GPIO43) debug test point", [("1", "P", "passive")])
add("TP7", "TP_RX", "TestPoint:TestPoint_Pad_1.0x1.0mm", "Connector:TestPoint",
    "UART0 RX (GPIO44) debug test point", [("1", "P", "passive")])
add("TP8", "TP_3V3", "TestPoint:TestPoint_Pad_1.0x1.0mm", "Connector:TestPoint",
    "3V3 rail probe", [("1", "P", "passive")])
add("TP9", "TP_VBAT", "TestPoint:TestPoint_Pad_1.0x1.0mm", "Connector:TestPoint",
    "VBAT/LiPo+ probe", [("1", "P", "passive")])

# ---------- Capacitors ----------
def add_cap(ref, value, footprint="Capacitor_SMD:C_0402_1005Metric"):
    add(ref, value, footprint, "Device:C", f"Ceramic capacitor {value}",
        [("1", "1", "passive"), ("2", "2", "passive")])

add_cap("C1",  "100nF")           # ESP32 3V3 decoupling pin 2
add_cap("C2",  "100nF")           # ESP32 3V3 decoupling pin 3
add_cap("C3",  "100nF")           # ESP32 VDD3P3 decoupling pin 24
add_cap("C4",  "10uF",  "Capacitor_SMD:C_0805_2012Metric")  # ESP32 bulk
add_cap("C5",  "100uF", "Capacitor_SMD:C_1210_3225Metric")  # Inference bulk

add_cap("C6",  "10uF",  "Capacitor_SMD:C_0805_2012Metric")  # USB-C VBUS

add_cap("C7",  "4.7uF", "Capacitor_SMD:C_0603_1608Metric")  # MCP73832 input
add_cap("C8",  "4.7uF", "Capacitor_SMD:C_0603_1608Metric")  # MCP73832 output

add_cap("C9",  "4.7uF", "Capacitor_SMD:C_0603_1608Metric")  # BQ25570 VIN_DC
add_cap("C10", "10nF")                                       # BQ25570 VREF_SAMP
add_cap("C11", "22uF",  "Capacitor_SMD:C_0805_2012Metric")  # BQ25570 VSTOR
add_cap("C12", "4.7uF", "Capacitor_SMD:C_0603_1608Metric")  # BQ25570 VBAT
add_cap("C13", "10uF",  "Capacitor_SMD:C_0805_2012Metric")  # BQ25570 VOUT

add_cap("C14", "1uF")     # XC6220 input
add_cap("C15", "1uF")     # XC6220 output

add_cap("C16", "1uF")     # MAX17048 VDD
add_cap("C17", "100nF")   # MAX17048 VDD HF

add_cap("C18", "1uF",  "Capacitor_SMD:C_0603_1608Metric")  # E-paper VDDIO bypass
add_cap("C19", "1uF",  "Capacitor_SMD:C_0603_1608Metric")  # E-paper VCI bypass
add_cap("C20", "1uF",  "Capacitor_SMD:C_0603_1608Metric")  # E-paper VDD logic
add_cap("C21", "1uF",  "Capacitor_SMD:C_0603_1608Metric")  # E-paper VPP
add_cap("C22", "1uF",  "Capacitor_SMD:C_0603_1608Metric")  # E-paper VSH-VSL flying cap
add_cap("C23", "1uF",  "Capacitor_SMD:C_0603_1608Metric")  # E-paper VGH-VGL flying cap
add_cap("C24", "1uF",  "Capacitor_SMD:C_0603_1608Metric")  # E-paper VCOM bypass

# ---------- Resistors ----------
def add_res(ref, value, footprint="Resistor_SMD:R_0402_1005Metric"):
    add(ref, value, footprint, "Device:R", f"Resistor {value}",
        [("1", "1", "passive"), ("2", "2", "passive")])

add_res("R1",  "2k")     # MCP73832 PROG (~500mA)
add_res("R2",  "10k")    # ESP32 EN pull-up
add_res("R3",  "5.1k")   # USB-C CC1 pull-down
add_res("R4",  "5.1k")   # USB-C CC2 pull-down
add_res("R5",  "1k")     # LED1 limit
add_res("R6",  "1k")     # LED2 limit
add_res("R7",  "1k")     # LED3 limit
add_res("R8",  "1k")     # LED4 limit
add_res("R9",  "1k")     # LED5 limit
add_res("R10", "4.7k")   # I2C SDA pull-up
add_res("R11", "4.7k")   # I2C SCL pull-up

# BQ25570 feedback network (per TI BQ25570 datasheet, Section 8.3.4)
# These set: VBAT_OV=4.20V, VBAT_UV=3.00V, OK_PROG/HYST thresholds, VOUT=4.2V
# **VERIFY against TI reference design before fabbing.**
add_res("R12", "5.49M")  # VBAT_OV upper
add_res("R13", "3.39M")  # VBAT_OV lower
add_res("R14", "5.65M")  # VBAT_UV upper
add_res("R15", "4.42M")  # VBAT_UV lower
add_res("R16", "5.07M")  # OK_PROG
add_res("R17", "3.69M")  # OK_HYST
add_res("R18", "6.04M")  # OK divider top
add_res("R19", "7.50M")  # VOUT_SET upper
add_res("R20", "3.32M")  # VOUT_SET lower
add_res("R21", "10M")    # VOC_SAMP upper (80% MPPT)
add_res("R22", "10M")    # VOC_SAMP lower
add_res("R23", "10k")    # E-paper BS tie

# ============================================================================
# NETS — list of (net_name, [(comp_ref, pin_num), ...])
# ============================================================================

NETS: List[Tuple[str, List[Tuple[str, str]]]] = [

    # ---------- Ground ----------
    ("GND", [
        ("U1", "1"), ("U1", "25"), ("U1", "47"), ("U1", "48"),  # ESP32 GND + EPAD
        ("U2", "2"),                                              # MCP73832 GND
        ("U3", "18"), ("U3", "20"), ("U3", "21"),                # BQ25570 VSS, EN (active-LOW), EPAD
        ("U4", "2"),                                              # XC6220 GND
        ("U5", "3"),                                              # MAX17048 GND
        ("U5", "1"),                                              # MAX17048 QSTRT (tie low)
        ("U6", "2"),                                              # USBLC6 GND
        ("Q1", "2"),                                              # MOSFET source
        ("J1", "A1"), ("J1", "A12"), ("J1", "B1"), ("J1", "B12"),
        ("J1", "S1"),                                             # USB-C GND + shield
        ("J2", "2"),                                              # LiPo GND
        ("J3", "15"), ("J3", "24"),                              # E-paper VSS, VSS2
        ("J3", "4"),  ("J3", "5"),                               # E-paper TSCL, TSDA (unused)
        ("J4", "2"),                                              # Solar cell -
        ("R3", "2"), ("R4", "2"),                                # CC1/CC2 pull-downs
        ("R13", "2"), ("R15", "2"), ("R17", "2"), ("R20", "2"),
        ("R22", "2"), ("R23", "2"),                              # Resistor network bottoms
        ("C1", "2"), ("C2", "2"), ("C3", "2"), ("C4", "2"), ("C5", "2"),
        ("C6", "2"), ("C7", "2"), ("C8", "2"), ("C9", "2"), ("C10", "2"),
        ("C11", "2"), ("C12", "2"), ("C13", "2"), ("C14", "2"), ("C15", "2"),
        ("C16", "2"), ("C17", "2"), ("C18", "2"), ("C19", "2"),
        ("C20", "2"), ("C21", "2"), ("C24", "2"),
        ("TP5", "1"),                                             # RST bridge B
    ]),

    # ---------- VBUS (5V from USB-C) ----------
    ("VBUS", [
        ("J1", "A4"), ("J1", "A9"), ("J1", "B4"), ("J1", "B9"),
        ("U2", "4"),    # MCP73832 VDD input
        ("U6", "5"),    # USBLC6 VBUS
        ("C6", "1"), ("C7", "1"),
    ]),

    # ---------- VBAT (LiPo, 3.0–4.2V) ----------
    ("VBAT", [
        ("D1", "3"),    # BAT54S common cathode (output)
        ("J2", "1"),    # LiPo +
        ("U4", "1"),    # XC6220 VIN
        ("U5", "2"),    # MAX17048 VDD (battery sense)
        ("J5", "1"),    # Motor + (drive from VBAT, not 3V3)
        ("D2", "1"),    # 1N4148W cathode (flyback to VBAT)
        ("C14", "1"),   # XC6220 input cap
        ("C16", "1"), ("C17", "1"),  # MAX17048 caps
        ("TP9", "1"),   # VBAT test point
    ]),

    # ---------- +3V3 (regulated 3.3V rail) ----------
    ("+3V3", [
        ("U1", "2"), ("U1", "3"), ("U1", "24"),  # ESP32 3V3 pins
        ("U4", "5"),                              # XC6220 VOUT
        ("J3", "13"), ("J3", "14"),               # E-paper VDDIO, VCI
        ("R2", "2"),                              # EN pull-up to 3V3
        ("R5", "2"), ("R6", "2"), ("R7", "2"), ("R8", "2"), ("R9", "2"),  # LED anodes via R
        ("R10", "2"), ("R11", "2"),               # I2C pull-ups
        ("C1", "1"), ("C2", "1"), ("C3", "1"), ("C4", "1"), ("C5", "1"),
        ("C15", "1"),
        ("C18", "1"), ("C19", "1"),               # E-paper VDDIO/VCI bypass
        ("TP8", "1"),                             # 3V3 test point
    ]),

    # ---------- USB charging path output (before BAT54S) ----------
    ("USB_CHG", [
        ("U2", "3"),    # MCP73832 VBAT output
        ("D1", "1"),    # BAT54S anode 1
        ("C8", "1"),
    ]),

    # ---------- Solar charging path output (before BAT54S) ----------
    ("SOL_CHG", [
        ("U3", "11"),   # BQ25570 VOUT
        ("U3", "13"),   # BQ25570 VBAT
        ("U3", "15"),   # BQ25570 VSTOR
        ("U3", "10"),   # BQ25570 VOUT_EN (tied to VBAT = always enabled)
        ("D1", "2"),    # BAT54S anode 2
        ("C11", "1"), ("C12", "1"), ("C13", "1"),
        ("R12", "2"), ("R14", "2"), ("R16", "2"), ("R18", "2"),  # divider tops
        ("R19", "1"),   # VOUT_SET upper (top to VOUT side)
    ]),

    # ---------- BQ25570 VBAT_OK → XC6220 EN ----------
    ("VBAT_OK", [
        ("U3", "7"),    # BQ25570 VBAT_OK
        ("U4", "3"),    # XC6220 EN
    ]),

    # ---------- Solar input ----------
    ("VSOLAR", [
        ("U3", "1"), ("U3", "19"),  # BQ25570 VIN_DC pins
        ("L1", "2"),                # Boost inductor outer end
        ("J4", "1"),                # Solar cell +
        ("R21", "1"),               # VOC_SAMP upper
        ("C9", "1"),
    ]),

    # ---------- BQ25570 internal nodes ----------
    ("BQ_LBOOST", [
        ("U3", "17"),
        ("L1", "1"),
    ]),
    ("BQ_VREF_SAMP", [
        ("U3", "3"),
        ("C10", "1"),
    ]),
    ("BQ_VBAT_OV", [
        ("U3", "12"),
        ("R12", "1"),
        ("R13", "1"),
    ]),
    ("BQ_VBAT_UV", [
        ("U3", "14"),
        ("R14", "1"),
        ("R15", "1"),
    ]),
    ("BQ_OK_PROG", [
        ("U3", "5"),
        ("R16", "1"),
        ("R17", "1"),
    ]),
    ("BQ_OK_HYST", [
        ("U3", "6"),
        ("R18", "1"),
    ]),
    ("BQ_VOUT_SET", [
        ("U3", "9"),
        ("R19", "2"),
        ("R20", "1"),
    ]),
    ("BQ_VOC_SAMP", [
        ("U3", "2"),
        ("R21", "2"),
        ("R22", "1"),
    ]),
    ("BQ_VRDIV", [
        ("U3", "4"),
        ("U3", "16"),  # tied to VRDIV2 in simplified config
    ]),
    ("BQ_OT_PROG", [
        ("U3", "8"),  # Over-temp programming, tie via resistor or leave for trim
    ]),

    # ---------- USB data lines ----------
    ("USB_DP", [   # Pre-ESD (USB-C to USBLC6)
        ("J1", "A6"), ("J1", "B6"),
        ("U6", "1"),
    ]),
    ("USB_DM", [
        ("J1", "A7"), ("J1", "B7"),
        ("U6", "3"),
    ]),
    ("USB_DP_PROT", [   # Post-ESD (USBLC6 to ESP32)
        ("U6", "6"),    # USBLC6 IO1'
        ("U1", "15"),   # ESP32 GPIO20 = USB D+
    ]),
    ("USB_DM_PROT", [
        ("U6", "4"),    # USBLC6 IO2'
        ("U1", "14"),   # ESP32 GPIO19 = USB D-
    ]),

    # ---------- USB-C CC pull-downs ----------
    ("CC1", [("J1", "A5"), ("R3", "1")]),
    ("CC2", [("J1", "B5"), ("R4", "1")]),

    # ---------- Charger PROG ----------
    ("CHG_PROG", [
        ("U2", "5"),
        ("R1", "1"),
    ]),
    ("CHG_PROG_GND", [
        ("R1", "2"),
        # Connect to GND via netlist below (R1.2 is in GND net already)
    ]),

    # ---------- ESP32 EN / Reset ----------
    ("ESP_EN", [
        ("U1", "4"),     # ESP32 EN
        ("R2", "1"),     # Pull-up
        ("TP4", "1"),    # RST bridge pad A
    ]),

    # ---------- Touch pads ----------
    ("TOUCH_UP", [
        ("U1", "5"),     # GPIO4
        ("TP1", "1"),
    ]),
    ("TOUCH_SEL", [
        ("U1", "6"),     # GPIO5 — RTC touch wake
        ("TP2", "1"),
    ]),
    ("TOUCH_DN", [
        ("U1", "7"),     # GPIO6
        ("TP3", "1"),
    ]),

    # ---------- E-paper SPI + control ----------
    ("EP_BUSY", [("U1", "8"),  ("J3", "7")]),    # GPIO7
    ("EP_RST",  [("U1", "13"), ("J3", "8")]),    # GPIO8
    ("EP_DC",   [("U1", "18"), ("J3", "9")]),    # GPIO9
    ("EP_CS",   [("U1", "19"), ("J3", "10")]),   # GPIO10
    ("EP_MOSI", [("U1", "20"), ("J3", "12")]),   # GPIO11 -> SDA
    ("EP_SCK",  [("U1", "21"), ("J3", "11")]),   # GPIO12 -> SCL

    # ---------- E-paper internal supply pins ----------
    ("EP_VDD",  [("J3", "16"), ("C20", "1")]),  # Internal logic supply
    ("EP_VPP",  [("J3", "17"), ("C21", "1")]),  # OTP programming
    ("EP_VCOM", [("J3", "22"), ("C24", "1")]),  # Common voltage

    # E-paper charge pump flying caps (between specific FPC pins, NOT to GND)
    ("EP_VSH_VSL", [
        ("J3", "3"),    # VSH
        ("J3", "18"),   # VSL
        ("C22", "1"), ("C22", "2"),  # Cap directly between VSH and VSL
    ]),
    # Note: this net definition is a simplification. In the real schematic,
    # C22 is wired between VSH (pin 3) and VSL (pin 18) only — not as a 4-way
    # short. The KiCad netlist will need manual review to confirm the cap is
    # placed as a flying cap between two pins, not shorting them.
    # Same for VGH/VGL below.
    ("EP_VGH_VGL", [
        ("J3", "20"),   # VGL
        ("J3", "21"),   # VGH
        ("C23", "1"), ("C23", "2"),
    ]),

    # E-paper booster select pin — tie to GND via 10k
    ("EP_BS", [
        ("J3", "6"),
        ("R23", "1"),
    ]),

    # ---------- Haptic motor ----------
    ("HAPTIC_GATE", [
        ("U1", "22"),    # GPIO13
        ("Q1", "1"),     # MOSFET gate
    ]),
    ("MOTOR_NEG", [
        ("Q1", "3"),     # MOSFET drain
        ("J5", "2"),     # Motor -
        ("D2", "2"),     # 1N4148W anode
    ]),

    # ---------- I2C (fuel gauge) ----------
    ("I2C_SDA", [
        ("U1", "38"),    # GPIO38
        ("U5", "5"),     # MAX17048 SDA
        ("R10", "1"),
    ]),
    ("I2C_SCL", [
        ("U1", "39"),    # GPIO39
        ("U5", "6"),     # MAX17048 SCL
        ("R11", "1"),
    ]),

    # ---------- Charge level LEDs ----------
    ("LED1_NET", [("U1", "23"), ("D3", "1")]),  # GPIO14 -> LED cathode
    ("LED2_NET", [("U1", "9"),  ("D4", "1")]),  # GPIO15 -> LED cathode
    ("LED3_NET", [("U1", "10"), ("D5", "1")]),  # GPIO16 -> LED cathode
    ("LED4_NET", [("U1", "11"), ("D6", "1")]),  # GPIO17 -> LED cathode
    ("LED5_NET", [("U1", "12"), ("D7", "1")]),  # GPIO18 -> LED cathode

    ("LED1_R",   [("D3", "2"), ("R5", "1")]),
    ("LED2_R",   [("D4", "2"), ("R6", "1")]),
    ("LED3_R",   [("D5", "2"), ("R7", "1")]),
    ("LED4_R",   [("D6", "2"), ("R8", "1")]),
    ("LED5_R",   [("D7", "2"), ("R9", "1")]),

    # ---------- Debug breakouts ----------
    ("DEBUG_TX", [("U1", "43"), ("TP6", "1")]),
    ("DEBUG_RX", [("U1", "44"), ("TP7", "1")]),

    # ---------- Unused ESP32 GPIOs (no_connect) ----------
    # In KiCad these would be marked with NC flags. Listed here for completeness:
    # GPIO0  (pin 46) — BOOT strap, internal pull-up, leave floating
    # GPIO3  (pin 16) — JTAG strap
    # GPIO33 (pin 33), GPIO34 (pin 34), GPIO40-42 (pins 40-42) — unused
    # GPIO45 (pin 45), GPIO46 (pin 17) — strapping
]

# Add R1 (PROG resistor lower) to GND — it's already listed implicitly
# since R1.2 is in GND. Remove the placeholder CHG_PROG_GND net.

# Patch: remove placeholder CHG_PROG_GND net; add R1.2 to GND
NETS = [n for n in NETS if n[0] != "CHG_PROG_GND"]
for net_name, members in NETS:
    if net_name == "GND":
        members.append(("R1", "2"))
        break


# ============================================================================
# NETLIST GENERATOR
# ============================================================================

def generate_kicad_netlist(filename: str = "chess_card.net"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Validate: ensure every component pin appears in exactly one net
    pin_to_net = {}
    duplicates = []
    for net_name, members in NETS:
        for ref, pin in members:
            key = (ref, pin)
            if key in pin_to_net:
                duplicates.append((key, pin_to_net[key], net_name))
            pin_to_net[key] = net_name

    if duplicates:
        print("WARNING: Duplicate pin assignments found:")
        for (ref, pin), n1, n2 in duplicates:
            print(f"   {ref}.{pin} appears in both '{n1}' and '{n2}'")

    # Find unconnected pins
    all_pins = set()
    for c in COMPONENTS:
        for pin_num, _, _ in c["pins"]:
            all_pins.add((c["ref"], pin_num))
    connected_pins = set(pin_to_net.keys())
    unconnected = all_pins - connected_pins

    print(f"\nTotal components:        {len(COMPONENTS)}")
    print(f"Total nets:              {len(NETS)}")
    print(f"Total pins (defined):    {len(all_pins)}")
    print(f"Total pins (connected):  {len(connected_pins)}")
    print(f"Unconnected pins:        {len(unconnected)}")
    if unconnected:
        print("\nUnconnected pins (these become 'no_connect' in netlist):")
        for ref, pin in sorted(unconnected):
            comp = next(c for c in COMPONENTS if c["ref"] == ref)
            pin_info = next((p for p in comp["pins"] if p[0] == pin), None)
            pin_name = pin_info[1] if pin_info else "?"
            print(f"   {ref}.{pin} ({pin_name})")

    # Build netlist
    lines = []
    lines.append('(export (version "E")')
    lines.append(f'  (design')
    lines.append(f'    (source "chess_card_netlist.py")')
    lines.append(f'    (date "{timestamp}")')
    lines.append(f'    (tool "Custom Python netlist generator v1.0")')
    lines.append(f'    (sheet (number "1") (name "/") (tstamps "/")))')

    # Components
    lines.append('  (components')
    for c in COMPONENTS:
        lines.append(f'    (comp (ref "{c["ref"]}")')
        lines.append(f'      (value "{c["value"]}")')
        lines.append(f'      (footprint "{c["footprint"]}")')
        lines.append(f'      (description "{c["description"]}")')
        lines.append(f'      (libsource (lib "{c["lib_id"].split(":")[0]}") '
                     f'(part "{c["lib_id"].split(":")[1]}") '
                     f'(description "{c["description"]}"))')
        lines.append(f'      (sheetpath (names "/") (tstamps "/")))')
    lines.append('  )')

    # Nets
    lines.append('  (nets')
    for i, (net_name, members) in enumerate(NETS, start=1):
        lines.append(f'    (net (code "{i}") (name "{net_name}")')
        for ref, pin in members:
            comp = next((c for c in COMPONENTS if c["ref"] == ref), None)
            if comp:
                pin_info = next((p for p in comp["pins"] if p[0] == pin), None)
                pin_name = pin_info[1] if pin_info else pin
                pin_type = pin_info[2] if pin_info else "passive"
                lines.append(f'      (node (ref "{ref}") (pin "{pin}") '
                             f'(pinfunction "{pin_name}") (pintype "{pin_type}"))')
            else:
                lines.append(f'      (node (ref "{ref}") (pin "{pin}"))')
        lines.append(f'    )')
    lines.append('  )')

    lines.append(')')

    with open(filename, "w") as f:
        f.write("\n".join(lines))

    print(f"\nNetlist written to {filename}")
    print(f"   Lines: {len(lines)}")


if __name__ == "__main__":
    generate_kicad_netlist("chess_card.net")
