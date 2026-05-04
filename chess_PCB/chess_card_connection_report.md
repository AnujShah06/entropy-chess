# Chess Card PCB v2 — Connection Report

Auto-generated from `chess_card_netlist.py`. Use this for visual review when drawing the schematic in KiCad eeschema, or for verifying the netlist before importing into Pcbnew.

**Total components:** 76
**Total nets:** 57

---

## Components

| Ref | Value | Footprint | Lib hint | Description |
|---|---|---|---|---|
| **C1** | 100nF | `Capacitor_SMD:C_0402_1005Metric` | `Device:C` | Ceramic capacitor 100nF |
| **C2** | 100nF | `Capacitor_SMD:C_0402_1005Metric` | `Device:C` | Ceramic capacitor 100nF |
| **C3** | 100nF | `Capacitor_SMD:C_0402_1005Metric` | `Device:C` | Ceramic capacitor 100nF |
| **C4** | 10uF | `Capacitor_SMD:C_0805_2012Metric` | `Device:C` | Ceramic capacitor 10uF |
| **C5** | 100uF | `Capacitor_SMD:C_1210_3225Metric` | `Device:C` | Ceramic capacitor 100uF |
| **C6** | 10uF | `Capacitor_SMD:C_0805_2012Metric` | `Device:C` | Ceramic capacitor 10uF |
| **C7** | 4.7uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 4.7uF |
| **C8** | 4.7uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 4.7uF |
| **C9** | 4.7uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 4.7uF |
| **C10** | 10nF | `Capacitor_SMD:C_0402_1005Metric` | `Device:C` | Ceramic capacitor 10nF |
| **C11** | 22uF | `Capacitor_SMD:C_0805_2012Metric` | `Device:C` | Ceramic capacitor 22uF |
| **C12** | 4.7uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 4.7uF |
| **C13** | 10uF | `Capacitor_SMD:C_0805_2012Metric` | `Device:C` | Ceramic capacitor 10uF |
| **C14** | 1uF | `Capacitor_SMD:C_0402_1005Metric` | `Device:C` | Ceramic capacitor 1uF |
| **C15** | 1uF | `Capacitor_SMD:C_0402_1005Metric` | `Device:C` | Ceramic capacitor 1uF |
| **C16** | 1uF | `Capacitor_SMD:C_0402_1005Metric` | `Device:C` | Ceramic capacitor 1uF |
| **C17** | 100nF | `Capacitor_SMD:C_0402_1005Metric` | `Device:C` | Ceramic capacitor 100nF |
| **C18** | 1uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 1uF |
| **C19** | 1uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 1uF |
| **C20** | 1uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 1uF |
| **C21** | 1uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 1uF |
| **C22** | 1uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 1uF |
| **C23** | 1uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 1uF |
| **C24** | 1uF | `Capacitor_SMD:C_0603_1608Metric` | `Device:C` | Ceramic capacitor 1uF |
| **D1** | BAT54S | `Package_TO_SOT_SMD:SOT-23` | `Diode:BAT54S` | Dual Schottky in series for power source OR-ing |
| **D2** | 1N4148W | `Diode_SMD:D_SOD-123` | `Diode:1N4148W` | Flyback diode for haptic motor |
| **D3** | Red | `LED_SMD:LED_0402_1005Metric` | `Device:LED` | Charge level LED — Red |
| **D4** | Red | `LED_SMD:LED_0402_1005Metric` | `Device:LED` | Charge level LED — Red |
| **D5** | Yellow | `LED_SMD:LED_0402_1005Metric` | `Device:LED` | Charge level LED — Yellow |
| **D6** | Green | `LED_SMD:LED_0402_1005Metric` | `Device:LED` | Charge level LED — Green |
| **D7** | Green | `LED_SMD:LED_0402_1005Metric` | `Device:LED` | Charge level LED — Green |
| **J1** | USB-C 16P SMD | `Connector_USB:USB_C_Receptacle_GCT_USB4085` | `Connector:USB_C_Receptacle_USB2.0_16P` | USB-C receptacle, USB 2.0 only |
| **J2** | JST-PH 2P SMD | `Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal` | `Connector:Conn_01x02` | JST-PH 2.0 mm SMD horizontal — LiPo battery connector |
| **J3** | FPC 24P 0.5mm | `Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal` | `Connector:FFC-FPC_24P` | FPC connector for 2.9" e-paper panel (24-pin, 0.5mm pitch) |
| **J4** | Solar Cell Pads | `TerminalBlock:TerminalBlock_bornier-2_P5.08mm` | `Connector_Generic:Conn_01x02` | Solder pads for solar cell wires |
| **J5** | ERM Motor Pads | `TerminalBlock:TerminalBlock_bornier-2_P5.08mm` | `Connector_Generic:Conn_01x02` | Solder pads for ERM coin haptic motor |
| **L1** | 22uH | `Inductor_SMD:L_0603_1608Metric` | `Device:L` | Boost inductor for BQ25570 |
| **Q1** | 2N7002 | `Package_TO_SOT_SMD:SOT-23` | `Transistor_FET:2N7002` | N-channel MOSFET for haptic motor drive |
| **R1** | 2k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 2k |
| **R2** | 10k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 10k |
| **R3** | 5.1k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 5.1k |
| **R4** | 5.1k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 5.1k |
| **R5** | 1k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 1k |
| **R6** | 1k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 1k |
| **R7** | 1k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 1k |
| **R8** | 1k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 1k |
| **R9** | 1k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 1k |
| **R10** | 4.7k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 4.7k |
| **R11** | 4.7k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 4.7k |
| **R12** | 5.49M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 5.49M |
| **R13** | 3.39M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 3.39M |
| **R14** | 5.65M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 5.65M |
| **R15** | 4.42M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 4.42M |
| **R16** | 5.07M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 5.07M |
| **R17** | 3.69M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 3.69M |
| **R18** | 6.04M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 6.04M |
| **R19** | 7.50M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 7.50M |
| **R20** | 3.32M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 3.32M |
| **R21** | 10M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 10M |
| **R22** | 10M | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 10M |
| **R23** | 10k | `Resistor_SMD:R_0402_1005Metric` | `Device:R` | Resistor 10k |
| **TP1** | Touch UP | `TestPoint:TestPoint_Pad_D8.0mm` | `Connector:TestPoint` | Capacitive touch pad — UP |
| **TP2** | Touch SELECT | `TestPoint:TestPoint_Pad_D8.0mm` | `Connector:TestPoint` | Capacitive touch pad — SELECT (RTC wake) |
| **TP3** | Touch DOWN | `TestPoint:TestPoint_Pad_D8.0mm` | `Connector:TestPoint` | Capacitive touch pad — DOWN |
| **TP4** | RST_BRIDGE_A | `TestPoint:TestPoint_Pad_1.5x1.5mm` | `Connector:TestPoint` | Reset bridge pad A (short to TP5 = hard reset) |
| **TP5** | RST_BRIDGE_B | `TestPoint:TestPoint_Pad_1.5x1.5mm` | `Connector:TestPoint` | Reset bridge pad B (GND) |
| **TP6** | TP_TX | `TestPoint:TestPoint_Pad_1.0x1.0mm` | `Connector:TestPoint` | UART0 TX (GPIO43) debug test point |
| **TP7** | TP_RX | `TestPoint:TestPoint_Pad_1.0x1.0mm` | `Connector:TestPoint` | UART0 RX (GPIO44) debug test point |
| **TP8** | TP_3V3 | `TestPoint:TestPoint_Pad_1.0x1.0mm` | `Connector:TestPoint` | 3V3 rail probe |
| **TP9** | TP_VBAT | `TestPoint:TestPoint_Pad_1.0x1.0mm` | `Connector:TestPoint` | VBAT/LiPo+ probe |
| **U1** | ESP32-S3-WROOM-2-N16R8 | `RF_Module:ESP32-S2-WROOM` | `RF_Module:ESP32-S3-WROOM-1` | Espressif WiFi/BT module — main MCU. Map to WROOM-2 footprint manually in KiCad. |
| **U2** | MCP73832T-2ACI/OT | `Package_TO_SOT_SMD:SOT-23-5` | `Battery_Management:MCP73832-2ACx_OT` | Microchip 500 mA single-cell LiPo charger, USB-C path |
| **U3** | BQ25570RGRR | `Package_DFN_QFN:QFN-20-1EP_3.5x3.5mm_P0.5mm_EP2x2mm` | `Battery_Management:BQ25570` | TI ultra-low-power solar harvester w/ MPPT and LiPo charging |
| **U4** | XC6220B331MR-G | `Package_TO_SOT_SMD:SOT-25` | `Regulator_Linear:XC6220Bxx` | Torex 1A 3.3V LDO with EN |
| **U5** | MAX17048G+T10 | `Package_TO_SOT_SMD:SOT-23-6` | `Battery_Management:MAX17048` | Maxim ModelGauge battery fuel gauge, I2C |
| **U6** | USBLC6-2SC6 | `Package_TO_SOT_SMD:SOT-23-6` | `Power_Protection:USBLC6-2SC6` | ST USB ESD protection (low capacitance) |

---

## Net List

Each net lists every component pin connected to it. Use this as the ground truth for wiring up the schematic.

### 1. `GND` (56 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C1 | 2 | 2 | 100nF |
| C2 | 2 | 2 | 100nF |
| C3 | 2 | 2 | 100nF |
| C4 | 2 | 2 | 10uF |
| C5 | 2 | 2 | 100uF |
| C6 | 2 | 2 | 10uF |
| C7 | 2 | 2 | 4.7uF |
| C8 | 2 | 2 | 4.7uF |
| C9 | 2 | 2 | 4.7uF |
| C10 | 2 | 2 | 10nF |
| C11 | 2 | 2 | 22uF |
| C12 | 2 | 2 | 4.7uF |
| C13 | 2 | 2 | 10uF |
| C14 | 2 | 2 | 1uF |
| C15 | 2 | 2 | 1uF |
| C16 | 2 | 2 | 1uF |
| C17 | 2 | 2 | 100nF |
| C18 | 2 | 2 | 1uF |
| C19 | 2 | 2 | 1uF |
| C20 | 2 | 2 | 1uF |
| C21 | 2 | 2 | 1uF |
| C24 | 2 | 2 | 1uF |
| J1 | A1 | GND | USB-C 16P SMD |
| J1 | A12 | GND | USB-C 16P SMD |
| J1 | B1 | GND | USB-C 16P SMD |
| J1 | B12 | GND | USB-C 16P SMD |
| J1 | S1 | SHIELD | USB-C 16P SMD |
| J2 | 2 | GND | JST-PH 2P SMD |
| J3 | 15 | VSS | FPC 24P 0.5mm |
| J3 | 24 | VSS2 | FPC 24P 0.5mm |
| J3 | 4 | TSCL | FPC 24P 0.5mm |
| J3 | 5 | TSDA | FPC 24P 0.5mm |
| J4 | 2 | SOL_MINUS | Solar Cell Pads |
| Q1 | 2 | S | 2N7002 |
| R1 | 2 | 2 | 2k |
| R3 | 2 | 2 | 5.1k |
| R4 | 2 | 2 | 5.1k |
| R13 | 2 | 2 | 3.39M |
| R15 | 2 | 2 | 4.42M |
| R17 | 2 | 2 | 3.69M |
| R20 | 2 | 2 | 3.32M |
| R22 | 2 | 2 | 10M |
| R23 | 2 | 2 | 10k |
| TP5 | 1 | P | RST_BRIDGE_B |
| U1 | 1 | GND | ESP32-S3-WROOM-2-N16R8 |
| U1 | 25 | GND | ESP32-S3-WROOM-2-N16R8 |
| U1 | 47 | GND | ESP32-S3-WROOM-2-N16R8 |
| U1 | 48 | EPAD | ESP32-S3-WROOM-2-N16R8 |
| U2 | 2 | GND | MCP73832T-2ACI/OT |
| U3 | 18 | VSS | BQ25570RGRR |
| U3 | 20 | EN | BQ25570RGRR |
| U3 | 21 | EPAD | BQ25570RGRR |
| U4 | 2 | GND | XC6220B331MR-G |
| U5 | 3 | GND | MAX17048G+T10 |
| U5 | 1 | QSTRT | MAX17048G+T10 |
| U6 | 2 | GND | USBLC6-2SC6 |

### 2. `VBUS` (8 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C6 | 1 | 1 | 10uF |
| C7 | 1 | 1 | 4.7uF |
| J1 | A4 | VBUS | USB-C 16P SMD |
| J1 | A9 | VBUS | USB-C 16P SMD |
| J1 | B4 | VBUS | USB-C 16P SMD |
| J1 | B9 | VBUS | USB-C 16P SMD |
| U2 | 4 | VDD | MCP73832T-2ACI/OT |
| U6 | 5 | VBUS | USBLC6-2SC6 |

### 3. `VBAT` (10 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C14 | 1 | 1 | 1uF |
| C16 | 1 | 1 | 1uF |
| C17 | 1 | 1 | 100nF |
| D1 | 3 | K | BAT54S |
| D2 | 1 | K | 1N4148W |
| J2 | 1 | VBAT | JST-PH 2P SMD |
| J5 | 1 | MOT_PLUS | ERM Motor Pads |
| TP9 | 1 | P | TP_VBAT |
| U4 | 1 | VIN | XC6220B331MR-G |
| U5 | 2 | VDD | MAX17048G+T10 |

### 4. `+3V3` (23 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C1 | 1 | 1 | 100nF |
| C2 | 1 | 1 | 100nF |
| C3 | 1 | 1 | 100nF |
| C4 | 1 | 1 | 10uF |
| C5 | 1 | 1 | 100uF |
| C15 | 1 | 1 | 1uF |
| C18 | 1 | 1 | 1uF |
| C19 | 1 | 1 | 1uF |
| J3 | 13 | VDDIO | FPC 24P 0.5mm |
| J3 | 14 | VCI | FPC 24P 0.5mm |
| R2 | 2 | 2 | 10k |
| R5 | 2 | 2 | 1k |
| R6 | 2 | 2 | 1k |
| R7 | 2 | 2 | 1k |
| R8 | 2 | 2 | 1k |
| R9 | 2 | 2 | 1k |
| R10 | 2 | 2 | 4.7k |
| R11 | 2 | 2 | 4.7k |
| TP8 | 1 | P | TP_3V3 |
| U1 | 2 | 3V3 | ESP32-S3-WROOM-2-N16R8 |
| U1 | 3 | 3V3 | ESP32-S3-WROOM-2-N16R8 |
| U1 | 24 | VDD3P3 | ESP32-S3-WROOM-2-N16R8 |
| U4 | 5 | VOUT | XC6220B331MR-G |

### 5. `USB_CHG` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C8 | 1 | 1 | 4.7uF |
| D1 | 1 | A1 | BAT54S |
| U2 | 3 | VBAT | MCP73832T-2ACI/OT |

### 6. `SOL_CHG` (13 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C11 | 1 | 1 | 22uF |
| C12 | 1 | 1 | 4.7uF |
| C13 | 1 | 1 | 10uF |
| D1 | 2 | A2 | BAT54S |
| R12 | 2 | 2 | 5.49M |
| R14 | 2 | 2 | 5.65M |
| R16 | 2 | 2 | 5.07M |
| R18 | 2 | 2 | 6.04M |
| R19 | 1 | 1 | 7.50M |
| U3 | 11 | VOUT | BQ25570RGRR |
| U3 | 13 | VBAT | BQ25570RGRR |
| U3 | 15 | VSTOR | BQ25570RGRR |
| U3 | 10 | VOUT_EN | BQ25570RGRR |

### 7. `VBAT_OK` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| U3 | 7 | VBAT_OK | BQ25570RGRR |
| U4 | 3 | EN | XC6220B331MR-G |

### 8. `VSOLAR` (6 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C9 | 1 | 1 | 4.7uF |
| J4 | 1 | SOL_PLUS | Solar Cell Pads |
| L1 | 2 | 2 | 22uH |
| R21 | 1 | 1 | 10M |
| U3 | 1 | VIN_DC | BQ25570RGRR |
| U3 | 19 | VIN_DC | BQ25570RGRR |

### 9. `BQ_LBOOST` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| L1 | 1 | 1 | 22uH |
| U3 | 17 | LBOOST | BQ25570RGRR |

### 10. `BQ_VREF_SAMP` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C10 | 1 | 1 | 10nF |
| U3 | 3 | VREF_SAMP | BQ25570RGRR |

### 11. `BQ_VBAT_OV` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R12 | 1 | 1 | 5.49M |
| R13 | 1 | 1 | 3.39M |
| U3 | 12 | VBAT_OV | BQ25570RGRR |

### 12. `BQ_VBAT_UV` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R14 | 1 | 1 | 5.65M |
| R15 | 1 | 1 | 4.42M |
| U3 | 14 | VBAT_UV | BQ25570RGRR |

### 13. `BQ_OK_PROG` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R16 | 1 | 1 | 5.07M |
| R17 | 1 | 1 | 3.69M |
| U3 | 5 | OK_PROG | BQ25570RGRR |

### 14. `BQ_OK_HYST` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R18 | 1 | 1 | 6.04M |
| U3 | 6 | OK_HYST | BQ25570RGRR |

### 15. `BQ_VOUT_SET` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R19 | 2 | 2 | 7.50M |
| R20 | 1 | 1 | 3.32M |
| U3 | 9 | VOUT_SET | BQ25570RGRR |

### 16. `BQ_VOC_SAMP` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R21 | 2 | 2 | 10M |
| R22 | 1 | 1 | 10M |
| U3 | 2 | VOC_SAMP | BQ25570RGRR |

### 17. `BQ_VRDIV` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| U3 | 4 | VRDIV | BQ25570RGRR |
| U3 | 16 | VRDIV2 | BQ25570RGRR |

### 18. `BQ_OT_PROG` (1 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| U3 | 8 | OT_PROG | BQ25570RGRR |

### 19. `USB_DP` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J1 | A6 | DP1 | USB-C 16P SMD |
| J1 | B6 | DP2 | USB-C 16P SMD |
| U6 | 1 | IO1 | USBLC6-2SC6 |

### 20. `USB_DM` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J1 | A7 | DN1 | USB-C 16P SMD |
| J1 | B7 | DN2 | USB-C 16P SMD |
| U6 | 3 | IO2 | USBLC6-2SC6 |

### 21. `USB_DP_PROT` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| U1 | 15 | IO20 | ESP32-S3-WROOM-2-N16R8 |
| U6 | 6 | IO1_P | USBLC6-2SC6 |

### 22. `USB_DM_PROT` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| U1 | 14 | IO19 | ESP32-S3-WROOM-2-N16R8 |
| U6 | 4 | IO2_P | USBLC6-2SC6 |

### 23. `CC1` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J1 | A5 | CC1 | USB-C 16P SMD |
| R3 | 1 | 1 | 5.1k |

### 24. `CC2` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J1 | B5 | CC2 | USB-C 16P SMD |
| R4 | 1 | 1 | 5.1k |

### 25. `CHG_PROG` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R1 | 1 | 1 | 2k |
| U2 | 5 | PROG | MCP73832T-2ACI/OT |

### 26. `ESP_EN` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R2 | 1 | 1 | 10k |
| TP4 | 1 | P | RST_BRIDGE_A |
| U1 | 4 | EN | ESP32-S3-WROOM-2-N16R8 |

### 27. `TOUCH_UP` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| TP1 | 1 | P | Touch UP |
| U1 | 5 | IO4 | ESP32-S3-WROOM-2-N16R8 |

### 28. `TOUCH_SEL` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| TP2 | 1 | P | Touch SELECT |
| U1 | 6 | IO5 | ESP32-S3-WROOM-2-N16R8 |

### 29. `TOUCH_DN` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| TP3 | 1 | P | Touch DOWN |
| U1 | 7 | IO6 | ESP32-S3-WROOM-2-N16R8 |

### 30. `EP_BUSY` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J3 | 7 | BUSY | FPC 24P 0.5mm |
| U1 | 8 | IO7 | ESP32-S3-WROOM-2-N16R8 |

### 31. `EP_RST` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J3 | 8 | RES_N | FPC 24P 0.5mm |
| U1 | 13 | IO8 | ESP32-S3-WROOM-2-N16R8 |

### 32. `EP_DC` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J3 | 9 | DC | FPC 24P 0.5mm |
| U1 | 18 | IO9 | ESP32-S3-WROOM-2-N16R8 |

### 33. `EP_CS` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J3 | 10 | CS_N | FPC 24P 0.5mm |
| U1 | 19 | IO10 | ESP32-S3-WROOM-2-N16R8 |

### 34. `EP_MOSI` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J3 | 12 | SDA | FPC 24P 0.5mm |
| U1 | 20 | IO11 | ESP32-S3-WROOM-2-N16R8 |

### 35. `EP_SCK` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J3 | 11 | SCL | FPC 24P 0.5mm |
| U1 | 21 | IO12 | ESP32-S3-WROOM-2-N16R8 |

### 36. `EP_VDD` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C20 | 1 | 1 | 1uF |
| J3 | 16 | VDD | FPC 24P 0.5mm |

### 37. `EP_VPP` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C21 | 1 | 1 | 1uF |
| J3 | 17 | VPP | FPC 24P 0.5mm |

### 38. `EP_VCOM` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C24 | 1 | 1 | 1uF |
| J3 | 22 | VCOM | FPC 24P 0.5mm |

### 39. `EP_VSH_VSL` (4 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C22 | 1 | 1 | 1uF |
| C22 | 2 | 2 | 1uF |
| J3 | 3 | VSH | FPC 24P 0.5mm |
| J3 | 18 | VSL | FPC 24P 0.5mm |

### 40. `EP_VGH_VGL` (4 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| C23 | 1 | 1 | 1uF |
| C23 | 2 | 2 | 1uF |
| J3 | 20 | VGL | FPC 24P 0.5mm |
| J3 | 21 | VGH | FPC 24P 0.5mm |

### 41. `EP_BS` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| J3 | 6 | BS | FPC 24P 0.5mm |
| R23 | 1 | 1 | 10k |

### 42. `HAPTIC_GATE` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| Q1 | 1 | G | 2N7002 |
| U1 | 22 | IO13 | ESP32-S3-WROOM-2-N16R8 |

### 43. `MOTOR_NEG` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D2 | 2 | A | 1N4148W |
| J5 | 2 | MOT_MINUS | ERM Motor Pads |
| Q1 | 3 | D | 2N7002 |

### 44. `I2C_SDA` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R10 | 1 | 1 | 4.7k |
| U1 | 38 | IO38 | ESP32-S3-WROOM-2-N16R8 |
| U5 | 5 | SDA | MAX17048G+T10 |

### 45. `I2C_SCL` (3 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| R11 | 1 | 1 | 4.7k |
| U1 | 39 | IO39 | ESP32-S3-WROOM-2-N16R8 |
| U5 | 6 | SCL | MAX17048G+T10 |

### 46. `LED1_NET` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D3 | 1 | K | Red |
| U1 | 23 | IO14 | ESP32-S3-WROOM-2-N16R8 |

### 47. `LED2_NET` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D4 | 1 | K | Red |
| U1 | 9 | IO15 | ESP32-S3-WROOM-2-N16R8 |

### 48. `LED3_NET` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D5 | 1 | K | Yellow |
| U1 | 10 | IO16 | ESP32-S3-WROOM-2-N16R8 |

### 49. `LED4_NET` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D6 | 1 | K | Green |
| U1 | 11 | IO17 | ESP32-S3-WROOM-2-N16R8 |

### 50. `LED5_NET` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D7 | 1 | K | Green |
| U1 | 12 | IO18 | ESP32-S3-WROOM-2-N16R8 |

### 51. `LED1_R` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D3 | 2 | A | Red |
| R5 | 1 | 1 | 1k |

### 52. `LED2_R` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D4 | 2 | A | Red |
| R6 | 1 | 1 | 1k |

### 53. `LED3_R` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D5 | 2 | A | Yellow |
| R7 | 1 | 1 | 1k |

### 54. `LED4_R` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D6 | 2 | A | Green |
| R8 | 1 | 1 | 1k |

### 55. `LED5_R` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| D7 | 2 | A | Green |
| R9 | 1 | 1 | 1k |

### 56. `DEBUG_TX` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| TP6 | 1 | P | TP_TX |
| U1 | 43 | TXD0 | ESP32-S3-WROOM-2-N16R8 |

### 57. `DEBUG_RX` (2 pins)

| Component | Pin | Pin Name | Value |
|---|---|---|---|
| TP7 | 1 | P | TP_RX |
| U1 | 44 | RXD0 | ESP32-S3-WROOM-2-N16R8 |


---

## Pin Cross-Reference (by component)

For each component, lists which net every pin is connected to. Useful for verifying nothing is left dangling.

### C1 — 100nF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `+3V3` |
| 2 | 2 | passive | `GND` |

### C2 — 100nF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `+3V3` |
| 2 | 2 | passive | `GND` |

### C3 — 100nF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `+3V3` |
| 2 | 2 | passive | `GND` |

### C4 — 10uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `+3V3` |
| 2 | 2 | passive | `GND` |

### C5 — 100uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `+3V3` |
| 2 | 2 | passive | `GND` |

### C6 — 10uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `VBUS` |
| 2 | 2 | passive | `GND` |

### C7 — 4.7uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `VBUS` |
| 2 | 2 | passive | `GND` |

### C8 — 4.7uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `USB_CHG` |
| 2 | 2 | passive | `GND` |

### C9 — 4.7uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `VSOLAR` |
| 2 | 2 | passive | `GND` |

### C10 — 10nF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_VREF_SAMP` |
| 2 | 2 | passive | `GND` |

### C11 — 22uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `SOL_CHG` |
| 2 | 2 | passive | `GND` |

### C12 — 4.7uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `SOL_CHG` |
| 2 | 2 | passive | `GND` |

### C13 — 10uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `SOL_CHG` |
| 2 | 2 | passive | `GND` |

### C14 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `VBAT` |
| 2 | 2 | passive | `GND` |

### C15 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `+3V3` |
| 2 | 2 | passive | `GND` |

### C16 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `VBAT` |
| 2 | 2 | passive | `GND` |

### C17 — 100nF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `VBAT` |
| 2 | 2 | passive | `GND` |

### C18 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `+3V3` |
| 2 | 2 | passive | `GND` |

### C19 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `+3V3` |
| 2 | 2 | passive | `GND` |

### C20 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `EP_VDD` |
| 2 | 2 | passive | `GND` |

### C21 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `EP_VPP` |
| 2 | 2 | passive | `GND` |

### C22 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `EP_VSH_VSL` |
| 2 | 2 | passive | `EP_VSH_VSL` |

### C23 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `EP_VGH_VGL` |
| 2 | 2 | passive | `EP_VGH_VGL` |

### C24 — 1uF

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `EP_VCOM` |
| 2 | 2 | passive | `GND` |

### D1 — BAT54S

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | A1 | passive | `USB_CHG` |
| 2 | A2 | passive | `SOL_CHG` |
| 3 | K | passive | `VBAT` |

### D2 — 1N4148W

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | K | passive | `VBAT` |
| 2 | A | passive | `MOTOR_NEG` |

### D3 — Red

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | K | passive | `LED1_NET` |
| 2 | A | passive | `LED1_R` |

### D4 — Red

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | K | passive | `LED2_NET` |
| 2 | A | passive | `LED2_R` |

### D5 — Yellow

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | K | passive | `LED3_NET` |
| 2 | A | passive | `LED3_R` |

### D6 — Green

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | K | passive | `LED4_NET` |
| 2 | A | passive | `LED4_R` |

### D7 — Green

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | K | passive | `LED5_NET` |
| 2 | A | passive | `LED5_R` |

### J1 — USB-C 16P SMD

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| A1 | GND | power_in | `GND` |
| A4 | VBUS | power_in | `VBUS` |
| A5 | CC1 | bidirectional | `CC1` |
| A6 | DP1 | bidirectional | `USB_DP` |
| A7 | DN1 | bidirectional | `USB_DM` |
| A9 | VBUS | power_in | `VBUS` |
| A12 | GND | power_in | `GND` |
| B1 | GND | power_in | `GND` |
| B4 | VBUS | power_in | `VBUS` |
| B5 | CC2 | bidirectional | `CC2` |
| B6 | DP2 | bidirectional | `USB_DP` |
| B7 | DN2 | bidirectional | `USB_DM` |
| B9 | VBUS | power_in | `VBUS` |
| B12 | GND | power_in | `GND` |
| S1 | SHIELD | power_in | `GND` |

### J2 — JST-PH 2P SMD

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | VBAT | power_in | `VBAT` |
| 2 | GND | power_in | `GND` |

### J3 — FPC 24P 0.5mm

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | GDR | passive | *(no connect)* |
| 2 | RES | passive | *(no connect)* |
| 3 | VSH | passive | `EP_VSH_VSL` |
| 4 | TSCL | passive | `GND` |
| 5 | TSDA | passive | `GND` |
| 6 | BS | passive | `EP_BS` |
| 7 | BUSY | output | `EP_BUSY` |
| 8 | RES_N | input | `EP_RST` |
| 9 | DC | input | `EP_DC` |
| 10 | CS_N | input | `EP_CS` |
| 11 | SCL | input | `EP_SCK` |
| 12 | SDA | input | `EP_MOSI` |
| 13 | VDDIO | power_in | `+3V3` |
| 14 | VCI | power_in | `+3V3` |
| 15 | VSS | power_in | `GND` |
| 16 | VDD | power_in | `EP_VDD` |
| 17 | VPP | passive | `EP_VPP` |
| 18 | VSL | passive | `EP_VSH_VSL` |
| 19 | VSH2 | passive | *(no connect)* |
| 20 | VGL | passive | `EP_VGH_VGL` |
| 21 | VGH | passive | `EP_VGH_VGL` |
| 22 | VCOM | passive | `EP_VCOM` |
| 23 | GDR2 | passive | *(no connect)* |
| 24 | VSS2 | power_in | `GND` |

### J4 — Solar Cell Pads

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | SOL_PLUS | passive | `VSOLAR` |
| 2 | SOL_MINUS | passive | `GND` |

### J5 — ERM Motor Pads

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | MOT_PLUS | passive | `VBAT` |
| 2 | MOT_MINUS | passive | `MOTOR_NEG` |

### L1 — 22uH

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_LBOOST` |
| 2 | 2 | passive | `VSOLAR` |

### Q1 — 2N7002

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | G | input | `HAPTIC_GATE` |
| 2 | S | passive | `GND` |
| 3 | D | passive | `MOTOR_NEG` |

### R1 — 2k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `CHG_PROG` |
| 2 | 2 | passive | `GND` |

### R2 — 10k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `ESP_EN` |
| 2 | 2 | passive | `+3V3` |

### R3 — 5.1k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `CC1` |
| 2 | 2 | passive | `GND` |

### R4 — 5.1k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `CC2` |
| 2 | 2 | passive | `GND` |

### R5 — 1k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `LED1_R` |
| 2 | 2 | passive | `+3V3` |

### R6 — 1k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `LED2_R` |
| 2 | 2 | passive | `+3V3` |

### R7 — 1k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `LED3_R` |
| 2 | 2 | passive | `+3V3` |

### R8 — 1k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `LED4_R` |
| 2 | 2 | passive | `+3V3` |

### R9 — 1k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `LED5_R` |
| 2 | 2 | passive | `+3V3` |

### R10 — 4.7k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `I2C_SDA` |
| 2 | 2 | passive | `+3V3` |

### R11 — 4.7k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `I2C_SCL` |
| 2 | 2 | passive | `+3V3` |

### R12 — 5.49M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_VBAT_OV` |
| 2 | 2 | passive | `SOL_CHG` |

### R13 — 3.39M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_VBAT_OV` |
| 2 | 2 | passive | `GND` |

### R14 — 5.65M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_VBAT_UV` |
| 2 | 2 | passive | `SOL_CHG` |

### R15 — 4.42M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_VBAT_UV` |
| 2 | 2 | passive | `GND` |

### R16 — 5.07M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_OK_PROG` |
| 2 | 2 | passive | `SOL_CHG` |

### R17 — 3.69M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_OK_PROG` |
| 2 | 2 | passive | `GND` |

### R18 — 6.04M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_OK_HYST` |
| 2 | 2 | passive | `SOL_CHG` |

### R19 — 7.50M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `SOL_CHG` |
| 2 | 2 | passive | `BQ_VOUT_SET` |

### R20 — 3.32M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_VOUT_SET` |
| 2 | 2 | passive | `GND` |

### R21 — 10M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `VSOLAR` |
| 2 | 2 | passive | `BQ_VOC_SAMP` |

### R22 — 10M

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `BQ_VOC_SAMP` |
| 2 | 2 | passive | `GND` |

### R23 — 10k

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | 1 | passive | `EP_BS` |
| 2 | 2 | passive | `GND` |

### TP1 — Touch UP

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | P | passive | `TOUCH_UP` |

### TP2 — Touch SELECT

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | P | passive | `TOUCH_SEL` |

### TP3 — Touch DOWN

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | P | passive | `TOUCH_DN` |

### TP4 — RST_BRIDGE_A

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | P | passive | `ESP_EN` |

### TP5 — RST_BRIDGE_B

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | P | passive | `GND` |

### TP6 — TP_TX

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | P | passive | `DEBUG_TX` |

### TP7 — TP_RX

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | P | passive | `DEBUG_RX` |

### TP8 — TP_3V3

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | P | passive | `+3V3` |

### TP9 — TP_VBAT

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | P | passive | `VBAT` |

### U1 — ESP32-S3-WROOM-2-N16R8

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | GND | power_in | `GND` |
| 2 | 3V3 | power_in | `+3V3` |
| 3 | 3V3 | power_in | `+3V3` |
| 4 | EN | input | `ESP_EN` |
| 5 | IO4 | bidirectional | `TOUCH_UP` |
| 6 | IO5 | bidirectional | `TOUCH_SEL` |
| 7 | IO6 | bidirectional | `TOUCH_DN` |
| 8 | IO7 | bidirectional | `EP_BUSY` |
| 9 | IO15 | bidirectional | `LED2_NET` |
| 10 | IO16 | bidirectional | `LED3_NET` |
| 11 | IO17 | bidirectional | `LED4_NET` |
| 12 | IO18 | bidirectional | `LED5_NET` |
| 13 | IO8 | bidirectional | `EP_RST` |
| 14 | IO19 | bidirectional | `USB_DM_PROT` |
| 15 | IO20 | bidirectional | `USB_DP_PROT` |
| 16 | IO3 | bidirectional | *(no connect)* |
| 17 | IO46 | bidirectional | *(no connect)* |
| 18 | IO9 | bidirectional | `EP_DC` |
| 19 | IO10 | bidirectional | `EP_CS` |
| 20 | IO11 | bidirectional | `EP_MOSI` |
| 21 | IO12 | bidirectional | `EP_SCK` |
| 22 | IO13 | bidirectional | `HAPTIC_GATE` |
| 23 | IO14 | bidirectional | `LED1_NET` |
| 24 | VDD3P3 | power_in | `+3V3` |
| 25 | GND | power_in | `GND` |
| 33 | IO33 | bidirectional | *(no connect)* |
| 34 | IO34 | bidirectional | *(no connect)* |
| 35 | IO35_NC | no_connect | *(no connect)* |
| 36 | IO36_NC | no_connect | *(no connect)* |
| 37 | IO37_NC | no_connect | *(no connect)* |
| 38 | IO38 | bidirectional | `I2C_SDA` |
| 39 | IO39 | bidirectional | `I2C_SCL` |
| 40 | IO40 | bidirectional | *(no connect)* |
| 41 | IO41 | bidirectional | *(no connect)* |
| 42 | IO42 | bidirectional | *(no connect)* |
| 43 | TXD0 | bidirectional | `DEBUG_TX` |
| 44 | RXD0 | bidirectional | `DEBUG_RX` |
| 45 | IO45 | bidirectional | *(no connect)* |
| 46 | IO0 | bidirectional | *(no connect)* |
| 47 | GND | power_in | `GND` |
| 48 | EPAD | power_in | `GND` |

### U2 — MCP73832T-2ACI/OT

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | STAT | open_collector | *(no connect)* |
| 2 | GND | power_in | `GND` |
| 3 | VBAT | power_out | `USB_CHG` |
| 4 | VDD | power_in | `VBUS` |
| 5 | PROG | input | `CHG_PROG` |

### U3 — BQ25570RGRR

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | VIN_DC | power_in | `VSOLAR` |
| 2 | VOC_SAMP | input | `BQ_VOC_SAMP` |
| 3 | VREF_SAMP | input | `BQ_VREF_SAMP` |
| 4 | VRDIV | output | `BQ_VRDIV` |
| 5 | OK_PROG | input | `BQ_OK_PROG` |
| 6 | OK_HYST | input | `BQ_OK_HYST` |
| 7 | VBAT_OK | output | `VBAT_OK` |
| 8 | OT_PROG | input | `BQ_OT_PROG` |
| 9 | VOUT_SET | input | `BQ_VOUT_SET` |
| 10 | VOUT_EN | input | `SOL_CHG` |
| 11 | VOUT | power_out | `SOL_CHG` |
| 12 | VBAT_OV | input | `BQ_VBAT_OV` |
| 13 | VBAT | power_out | `SOL_CHG` |
| 14 | VBAT_UV | input | `BQ_VBAT_UV` |
| 15 | VSTOR | power_out | `SOL_CHG` |
| 16 | VRDIV2 | output | `BQ_VRDIV` |
| 17 | LBOOST | passive | `BQ_LBOOST` |
| 18 | VSS | power_in | `GND` |
| 19 | VIN_DC | power_in | `VSOLAR` |
| 20 | EN | input | `GND` |
| 21 | EPAD | power_in | `GND` |

### U4 — XC6220B331MR-G

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | VIN | power_in | `VBAT` |
| 2 | GND | power_in | `GND` |
| 3 | EN | input | `VBAT_OK` |
| 4 | NC | no_connect | *(no connect)* |
| 5 | VOUT | power_out | `+3V3` |

### U5 — MAX17048G+T10

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | QSTRT | input | `GND` |
| 2 | VDD | power_in | `VBAT` |
| 3 | GND | power_in | `GND` |
| 4 | ALRT | open_collector | *(no connect)* |
| 5 | SDA | bidirectional | `I2C_SDA` |
| 6 | SCL | input | `I2C_SCL` |

### U6 — USBLC6-2SC6

| Pin | Pin Name | Type | Connected to |
|---|---|---|---|
| 1 | IO1 | bidirectional | `USB_DP` |
| 2 | GND | power_in | `GND` |
| 3 | IO2 | bidirectional | `USB_DM` |
| 4 | IO2_P | bidirectional | `USB_DM_PROT` |
| 5 | VBUS | power_in | `VBUS` |
| 6 | IO1_P | bidirectional | `USB_DP_PROT` |

