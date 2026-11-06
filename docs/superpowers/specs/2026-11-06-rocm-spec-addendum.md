# ROCM — Spec Addendum: Gap Review & Board Architecture

Date: 2026-11-06 · Author: Gage · Status: pending review

This addendum amends the base spec, **`2026-10-12-esp32-sensor-board-design.md`** (piSensor repo, branch `esp32-board-spec`). The base spec is still correct. Where the two differ, this document wins.

ROCM (Realtime Operations Count Monitor) is the ESP32-C3 board that replaces the Raspberry Pi Zero 2 W stud counters on the heading machines. It reports to Connect the same way `sensor.py` v4 does.

## 1. Project state at review

| Item | State |
|---|---|
| Schematic (`ROCM.kicad_sch`) | Fully captured, ERC 0 violations (2026-11-06) |
| PCB (`ROCM.kicad_pcb`) | Not started (empty file, no outline) |
| Firmware | Not started (spec only) |
| Enclosure | Not started |

## 2. Decisions made in this review

| Topic | Decision | Changes the base spec? |
|---|---|---|
| Sensor | 5 V-rated inductive sensors, as used on the Pis today. The 5 V supply and NPN/PNP JP1 stay. | No |
| Power | USB wall adapter at each machine. USB-C (J1) stays. | No |
| Enclosure | **3D-printed custom case**, designed in Fusion around the board's STEP. The board comes first. | Yes: replaces the Hammond 1554 suggestion |
| Sensor entry | **M8 3-pin panel socket in the case wall → its flying leads → 3-pin pluggable screw terminal on the board.** Sensors swap without opening the case. | Yes: replaces JST GH J2 |
| Power entry | **IP67 panel-mount USB-C extension** (capped female outside, short male lead inside into J1). USB programming stays possible through the wall. | Yes: closes base open item 2 |
| Expansion | Stay minimal: one sensor input. Spare GPIO0/1/10 go to test pads only. | No |

## 3. Schematic vs. base spec: netlist check

The connectivity graph was compared against the base spec's pin map and the ESP32-C3-MINI-1 pinout. **All signal nets match.**

| Net | Connection | OK |
|---|---|---|
| HALL | U5:2 → U1:6 (GPIO3) | ✓ |
| SENSOR_IN | U3:4 → U1:18 (GPIO4) | ✓ |
| LED_R / G / B | Q1/Q2/Q3 gate → U1:19/20/21 (GPIO5/6/7) | ✓ |
| STRAP_IO2 / IO8 / BOOT | 10 k pull-ups → U1:5 / U1:22 / U1:23 | ✓ |
| USB_DN / USB_DP | J1 → U4 (pairs 1/6, 3/4) → U1:26/27 (GPIO18/19) | ✓ |
| UART_RX / TX | TP6/TP5 → U1:30/31 | ✓ |
| CC1 / CC2 | R1 / R2 5.1 k to GND | ✓ |
| +3V3 | U2:5 (AP2112K, EN tied to VIN) | ✓ |
| Sensor path | J2:3 → D2 → R7 → JP1 → R8 / C6 → U3:2 | ✓ |

## 4. Gaps and resolutions (applied in Slice 2)

### Electrical / schematic

| # | Gap | Resolution | Refdes / net |
|---|---|---|---|
| 1 | The JST GH 1.25 mm sensor connector needs fine hand-crimping. | Replace it with a 3-pin, 3.5 mm pitch pluggable terminal header and plug (e.g. Phoenix MC 1,5/3-G-3,5 + MC 1,5/3-ST-3,5, or a stocked PCBWay equivalent). Pin 1 = SENSOR_5V, 2 = GND, 3 = SENSOR_RAW. Silkscreen `+5V BN \| GND BU \| SIG BK`. | J2 |
| 2 | The Hall symbol is `DRV5033FAxDBZ` but the BOM MPN is `DRV5032FADBZR`, and the two parts have different output stages. | Check the DRV5032FA output type and SOT-23 pinout on the datasheet. Swap in the matching symbol. Add a 10 k pull-up to 3V3 only if the output is open-drain. | U5, HALL |
| 3 | The LED is the Inolux IN-P55TATRGB (PLCC-6, separate anodes), not the base spec's PLCC-4. Its pin assignment hasn't been checked. | Confirm on the datasheet that pins 1/2/3 are the B/R/G cathodes and 4/5/6 are the anodes. Recompute R9–R11 from Vf for ≤ 15 mA per die. | LED1, R9–R11 |
| 4 | The 2N7002 gates float during reset and boot, so the LED can flash. | Add 100 k from each gate to GND. | Q1–Q3, new R |
| 5 | SENSOR_5V has no local decoupling at the connector. | Add 1 µF + 100 nF from SENSOR_5V to GND next to J2. | SENSOR_5V, new C |
| 6 | Spare GPIOs have no access for future bodges. | Add test pads on GPIO0 (U1:12), GPIO1 (U1:13) and GPIO10 (U1:16), replacing their no-connect flags. | U1, new TP |
| 7 | The schematic has no mounting holes. | Add 4× M3 (3.2 mm), connected to no net. The case uses M3 heat-set inserts. | new H1–H4 |
| 8 | Parts haven't been checked for sourcing, and the BOM has no LCSC numbers. | Run stock and availability checks for every MPN. Pre-approve substitutes for the module, AP2112K, '1G17, DRV5032 and LED. | BOM |

### Mechanical / system

| # | Gap (base-spec open item) | Resolution |
|---|---|---|
| 9 | Enclosure (open item 3) | 3D-printed case. The board outline is free; the case follows the STEP. |
| 10 | Power entry (open item 2) | IP67 panel-mount USB-C extension. |
| 11 | Sensor-side connector | Sensors need an M8 3-pin male plug. Either buy 5 V sensors with M8 plugs, or fit field-wireable M8 male plugs (screw terminals inside) to the existing pigtails. |
| 12 | Antenna path | RP-SMA bulkhead pigtail through the case **top** wall. The antenna sits outside, clear of machine steel. |

### Still open (none block the PCB)

- Firmware update delivery method. The partitions already support every option.
- Value of the shared setup password, and confirming Connect accepts `rssi` and `fw`.
- Minimum real stud pulse width, to be measured with a logic analyser before setting the filter.
- Case sealing: TPU gasket vs. O-ring groove, and ASA vs. PETG for oil and heat near the machine.
- Exact part picks for the M8 panel socket, USB-C panel extension, RP-SMA pigtail, antenna and magnet.

## 5. Board architecture

**Stack-up.** 2 layers, 1.6 mm FR-4, 1 oz copper, ENIG. All SMD parts on the top side; J1 and J2 have through-hole tabs or pins.

**Size and holes.** Target about 50 × 40 mm with rounded corners and 4× M3 near the corners.

**Edge plan.** Cables enter from the bottom so water and oil drip away from the entries.

```
          top wall: RP-SMA bulkhead
 ┌───────────────────────────────────────┐
 │ H1        U1 ESP32-C3-MINI-1U       H2 │  u.FL end of module toward top
 │           (module keep-out)            │
 │                                        │
 │   SW1 SW2      LED1 ◉       U5 Hall ▣  │  LED under lid window / light pipe
 │   TP1–TP9      U2 LDO   U3 '1G17 Q1–3  │
 │                                        │
 │ H3  D1 F1 U4               D2 F2 JP1 H4│  protection right behind connectors
 └──────[ J1 USB-C ]────────[ J2 3-pin ]──┘
          bottom wall: USB-C panel extension, M8 panel socket
```

**Placement rules**
- TVS and ESD parts (D1, U4, D2) go within a few mm of their connectors, with short, wide ground returns.
- USB D+/D− run as a short 90 Ω differential pair, kept away from the sensor path.
- Leave room under and around the u.FL end of U1 for the pigtail connector and its bend radius.
- LED1 and U5 sit at round-number X/Y coordinates, which are recorded on the fab drawing for the case.
- SW1, SW2 and all test pads stay reachable with the lid off.

**Copper.** GND pour on both layers, stitched with vias around the edges and around U1. No copper in the module's antenna keep-out (moot for the -1U, but harmless).

**Silkscreen.** `ROCM` with the revision and date, `NPN | PNP` at JP1, M8 wire colours at J2, a blank label box for head ID and MAC, and LED and Hall markers.

**Case handoff.** Export the STEP after placement (Slice 3). The Fusion case takes from it the M3 boss positions, the J1 and J2 cut-out heights, the LED window position, the Hall magnet marking, and the RP-SMA hole position.

## 6. Delivery slices

| Slice | Scope | Exit check |
|---|---|---|
| 1 | This addendum | Gage approves |
| 2 | Schematic patch: gaps 1–8 (kicad-genie `sch_*`, `lib_*`) | ERC 0; no JST GH in BOM; Hall MPN matches its symbol; all MPNs in stock |
| 3 | Outline, holes, placement per §5; STEP export | `pcb_placement_quality_gate` passes; Gage approves placement; STEP delivered |
| 4 | Routing, pours, stitching | DRC 0; PCBWay DFM profile check passes; EMC checks reviewed |
| 5 | Fab package: Gerbers, drill, BOM, pick-and-place for PCBWay | Order 5 assembled prototypes |
| In parallel | Fusion case (after Slice 3); firmware in piSensor | — |
