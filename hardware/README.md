# piSensor ESP32 board — KiCad build guide

Design spec: [`docs/superpowers/specs/2026-10-12-esp32-sensor-board-design.md`](../docs/superpowers/specs/2026-10-12-esp32-sensor-board-design.md)

KiCad project: `hardware/pisensor-board/` (KiCad 10, single schematic sheet).
Libraries: KiCad standard library + `PCM_Espressif` (Plugin and Content Manager). PCBWay Fabrication Toolkit installed for export.

## Status

| Section | State |
|---|---|
| 1. Power (USB-C, protection, 3.3 V) | Reviewed; two touches left (below) |
| 2. Microcontroller (ESP32-C3 module) | Next |
| 3. Sensor input | Not started |
| 4. Hall sensor + status LED | Not started |
| Footprints, layout, DRC, PCBWay export | Not started |

Workflow: draw a section → ERC → screenshot or push for review → next section.

## Net names shared between sections

| Net / label | From | To |
|---|---|---|
| `VBUS` | J1 VBUS (before F1) | D1, U4 pin 5 |
| `+5V` | F1 output | U2 VIN/EN, C1, sensor PTC, LED anode |
| `+3V3` | U2 VOUT | U1 3V3, pull-ups, U3, U5 |
| `USB_DP` | J1 D+ (A6/B6) → U4 pins 3/4 | U1 IO19 |
| `USB_DN` | J1 D− (A7/B7) → U4 pins 1/6 | U1 IO18 |
| `SENSOR` | U3 output | U1 IO4 |
| `HALL` | U5 output | U1 IO3 |
| `LED_R` / `LED_G` / `LED_B` | U1 IO5 / IO6 / IO7 | Q1 / Q2 / Q3 gates |

## 1. Power

| Ref | Symbol | Value | Footprint |
|---|---|---|---|
| J1 | `USB_C_Receptacle_USB2.0_16P` | USB-C (GCT USB4105-GF-A) | `USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal` |
| R1, R2 | `R` | 5.1k | `R_0603_1608Metric` |
| D1 | `D_TVS` (bidirectional) | SMF5.0CA | `D_SMF` |
| F1 | `Polyfuse` | 500mA (MF-MSMF050-2) | `Fuse_1812_4532Metric` |
| U4 | `USBLC6-2SC6` | USBLC6-2SC6 | `SOT-23-6` |
| U2 | `AP2112K-3.3` | AP2112K-3.3 | `SOT-23-5` |
| C1, C2 | `C` | 10µF | `C_0805_2012Metric` |

Wiring:
- J1 VBUS → `VBUS`; GND and SHIELD → GND; SBU1/SBU2 → no-connect.
- CC1 → R1 → GND; CC2 → R2 → GND (separate resistors).
- Both D+ pins together → `USB_DP`; both D− pins together → `USB_DN`.
- D1 across `VBUS`–GND. F1 from `VBUS` to `+5V`.
- U4: pin 5 → `VBUS`, pin 2 → GND, pins 1 and 6 → `USB_DN`, pins 3 and 4 → `USB_DP`. Label the wires on **both** sides of U4 so each line is one net.
- U2: VIN and EN → `+5V`, GND → GND, VOUT → `+3V3`, NC → no-connect. C1 at input, C2 at output, both to GND.
- `PWR_FLAG` on `+5V` and on GND.

Remaining on the current schematic:
- [ ] Label the J1-side wires into U4 (`USB_DN` into pin 1, `USB_DP` into pin 3).
- [ ] Change D1 value to SMF5.0CA (bidirectional, matches the symbol).

## 2. Microcontroller

| Ref | Symbol | Value | Footprint |
|---|---|---|---|
| U1 | `ESP32-C3-MINI-1U` (PCM_Espressif) | ESP32-C3-MINI-1U-N4 | from symbol |
| C3 | `C` | 22µF | `C_0805_2012Metric` |
| C4 | `C` | 100nF | `C_0603_1608Metric` |
| C5 | `C` | 1µF | `C_0603_1608Metric` |
| R3–R6 | `R` | 10k | `R_0603_1608Metric` |
| SW1, SW2 | `SW_Push` | RESET, BOOT | `SW_SPST_PTS810` |
| TP1–TP6 | `TestPoint` | — | `TestPoint_Pad_D1.5mm` |

Wiring:
- 3V3 → `+3V3`; C3 and C4 from `+3V3` to GND beside the pin.
- All GND pins and the centre pad → GND.
- EN: R3 to `+3V3`, C5 to GND, SW1 to GND.
- IO9: R4 to `+3V3`, SW2 to GND.
- IO2: R5 to `+3V3`. IO8: R6 to `+3V3`.
- IO18 → `USB_DN`, IO19 → `USB_DP` (do not swap).
- IO3 → `HALL`, IO4 → `SENSOR`, IO5/6/7 → `LED_R`/`LED_G`/`LED_B`.
- Test points: TP1 `+3V3`, TP2 GND, TP3 EN, TP4 IO9, TP5 TXD0 (IO21), TP6 RXD0 (IO20).
- All other IO and NC pins → no-connect.

## 3. Sensor input

| Ref | Symbol | Value | Footprint |
|---|---|---|---|
| J2 | `Conn_01x03` | JST GH 3-pin (BM03B-GHS-TBT) | `JST_GH_BM03B-GHS-TBT_1x03-1MP_P1.25mm_Vertical` |
| F2 | `Polyfuse` | ~100mA (MF-PSMF010X-2) | `Fuse_0805_2012Metric` |
| D2 | `D_TVS` (bidirectional) | SMF5.0CA | `D_SMF` |
| JP1 | `SolderJumper_3_Open` | NPN/PNP | `SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm` |
| R7 | `R` | 10k | `R_0603_1608Metric` |
| R8 | `R` | 1k | `R_0603_1608Metric` |
| C6 | `C` | 47nF | `C_0603_1608Metric` |
| U3 | `74LVC1G17` | SN74LVC1G17DBVR | `SOT-23-5` |
| C7 | `C` | 100nF | `C_0603_1608Metric` |

Wiring:
- J2 pin 1 (brown) → F2 → `+5V`; pin 2 (blue) → GND; pin 3 (black) → `SENS_RAW`.
- D2 across `SENS_RAW`–GND, at the connector.
- `SENS_RAW` → R7 → JP1 centre; JP1 one side → `+5V` (NPN), other side → GND (PNP). Silkscreen `NPN | PNP`.
- `SENS_RAW` → R8 → U3 input; C6 from U3 input to GND.
- U3 VCC → `+3V3` with C7 to GND; U3 GND → GND; U3 output → `SENSOR`.

Footprints for J2 and JP1: confirm the exact names in the footprint browser.

## 4. Hall sensor + status LED

| Ref | Symbol | Value | Footprint |
|---|---|---|---|
| U5 | custom 3-pin (VDD, OUT, GND) | DRV5032 (push-pull variant) | `SOT-23` |
| C8 | `C` | 100nF | `C_0603_1608Metric` |
| LED1 | `LED_RAGB` (common anode) | RGB, PLCC-4 | per chosen part |
| Q1–Q3 | `2N7002` | 2N7002 | `SOT-23` |
| R9 | `R` | 150Ω (red) | `R_0603_1608Metric` |
| R10, R11 | `R` | 100Ω (green, blue) | `R_0603_1608Metric` |

Wiring:
- U5 VDD → `+3V3` with C8 to GND; GND → GND; OUT → `HALL`.
- LED1 anode → `+5V`. Each cathode → its resistor → drain of Q1/Q2/Q3; sources → GND; gates ← `LED_R`/`LED_G`/`LED_B`.

## After the schematic

1. Fill `Manufacturer` and `MPN` on every part (Symbol Fields Table).
2. ERC clean.
3. Choose the enclosure, then draw the board outline (about 45 × 35 mm, four M3 holes).
4. Place connectors, LED and Hall sensor first, then the rest (see the placement sketch in the spec discussion: power left, module top centre, sensor chain right).
5. Route, ground pour both layers, DRC with PCBWay's rules.
6. Export with the PCBWay toolkit; order 5 assembled prototypes.

## Review notes (mistakes caught so far)

- The USBLC6-2SC6 symbol was flipped, putting VBUS on GND. Wire by pin number, not by symbol orientation.
- Data labels were swapped across U4 (D− came out as `USB_DP`). Pins 1/6 and 3/4 are the same line inside the chip.
- Capacitors were placed without their GND side wired.
- The TVS symbol was bidirectional while the part number was unidirectional.
