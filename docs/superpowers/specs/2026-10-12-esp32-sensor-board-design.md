# piSensor ESP32 Board — Design Spec

Date: 2026-10-12 · Author: Gage · Status: approved design, pending spec review

## Overview

A custom ESP32-C3 board replaces the Raspberry Pi Zero 2 W on each heading machine. It counts studs from one inductive sensor and reports to Connect exactly as `sensor.py` v4 does, sealed against water and oil.

**Requirements (agreed)**

- One LJ8A3-style 5 V inductive sensor per board, NPN or PNP (selectable).
- WiFi only. Reliable connection is the top priority.
- Powered from USB 5 V.
- Sealed (water/oil), plastic enclosure, on heading machines.
- Sensor plugs in through an M8 3-pin quick-connect.
- No screen. One RGB status LED. Magnetic (Hall) trigger to enter setup mode.
- First boot: the board broadcasts its own WiFi; a config page sets plant WiFi and device settings (everything `.env` holds today).
- Reports to Connect with the current telemetry API; firmware and Connect may change.
- Flash laid out for over-the-air updates; delivery method decided later.
- Quantity: 11 for the plant plus spares, about 15. Designed in KiCad by Gage, built and assembled by PCBWay.

**Out of scope for this version:** display, real-time clock chip, Ethernet, a status web page in run mode, detecting a disconnected sensor.

## Block diagram

```
Power:   USB-C 5 V → TVS + PTC → +5V ─┬→ AP2112K 3.3 V → ESP32-C3-MINI-1U
                                      ├→ PTC → M8 pin 1 (sensor supply)
                                      └→ RGB LED anode

Sensor:  M8 pin 4 → TVS → NPN/PNP pull (JP1) → 1 kΩ / 47 nF → 74LVC1G17 → GPIO4
Setup:   magnet through lid → DRV5032 Hall switch → GPIO3
Status:  GPIO5/6/7 → 2N7002 ×3 → RGB LED cathodes
USB:     D+/D− → USBLC6-2SC6 → GPIO19/18
Radio:   module u.FL → RP-SMA bulkhead → sealed 2.4 GHz antenna
```

## Hardware

### Power

- USB-C receptacle, USB 2.0 type (GCT USB4105-GF-A).
- CC1 and CC2 each pulled to GND with 5.1 kΩ, so USB-C chargers supply 5 V.
- VBUS: SMF5.0A TVS to GND, then a 500 mA-hold PTC (Bourns MF-MSMF050-2) → net `+5V`.
- 3.3 V from an AP2112K-3.3 (600 mA). 10 µF in, 10 µF out; 22 µF + 100 nF at the module's 3V3 pin. The C3 peaks around 350 mA while transmitting.
- D+/D− through a USBLC6-2SC6 ESD array to GPIO19/GPIO18.

### Microcontroller

- ESP32-C3-MINI-1U-N4: 4 MB flash, u.FL antenna connector, certified module.
- Antenna: u.FL to RP-SMA bulkhead pigtail (with O-ring) through the enclosure wall, sealed screw-on 2.4 GHz antenna outside, positioned clear of the machine's steel.
- EN: 10 kΩ pull-up to 3V3, 1 µF to GND, RESET button to GND.
- GPIO9 (boot strap): 10 kΩ pull-up, BOOT button to GND. Firmware also treats a 5 s hold as "enter setup".
- GPIO2 and GPIO8 (boot straps): 10 kΩ pull-ups, otherwise unused.
- Test pads: 3V3, GND, EN, GPIO9, TX (GPIO21), RX (GPIO20).

### Sensor input

- Connector on the board: JST GH 3-pin latching (BM03B-GHS-TBT). A panel-mount M8 3-pin female socket in the enclosure wall, with pre-wired leads crimped to a GH housing, plugs in.
- M8 pinout (standard): pin 1 brown = +5 V, pin 3 blue = GND, pin 4 black = signal.
- Sensor supply: `+5V` through an ~100 mA-hold PTC (e.g. Bourns MF-PSMF010X-2) to pin 1.
- Signal path, in order:
  1. SMF5.0A TVS to GND at the connector.
  2. 10 kΩ to a 3-pad solder jumper JP1: centre = signal, one side = `+5V` (NPN, pull-up), other side = GND (PNP, pull-down). Silkscreen: `NPN | PNP`.
  3. 1 kΩ series resistor, 47 nF to GND (≈ 50 µs filter).
  4. SN74LVC1G17 Schmitt buffer powered at 3.3 V (input tolerates 5 V) → GPIO4.
- Firmware ignores pulses shorter than a minimum width (default 3 ms) and counts the edge that matches the sensor type: PNP counts rising, NPN counts falling.

### Setup trigger

- TI DRV5032 omnipolar Hall switch (SOT-23, push-pull output) → GPIO3. A magnet held on a marked spot on the lid for 5 s enters setup mode. No hole in the enclosure; no glass reed to crack under vibration.
- Place it where the board sits closest to the lid. Confirm trigger distance through the real lid.

### Status LED

- PLCC-4 common-anode RGB LED, anode on `+5V`, each cathode switched by a 2N7002 low-side MOSFET from GPIO5/6/7. Series resistors sized from the chosen LED's datasheet for about 10–20 mA (roughly 150 Ω red, 100 Ω green/blue).
- Sits under a light pipe or a clear lid section.

| LED | Meaning |
|---|---|
| Slow blue blink | Setup mode, broadcasting its own network |
| Fast yellow blink | Joining plant WiFi |
| Green, white flash per count | Running, last report acknowledged |
| Solid amber | On WiFi, Connect not answering; counts buffered |
| Red blink | Token rejected or setup incomplete |

### Pin map

| ESP32-C3 pin | Use |
|---|---|
| GPIO3 | Hall sensor (setup trigger) |
| GPIO4 | Sensor input (from 74LVC1G17) |
| GPIO5 / 6 / 7 | Status LED red / green / blue (via 2N7002) |
| GPIO9 | BOOT button, boot strap, pull-up |
| GPIO2, GPIO8 | Boot straps, pull-ups, unused |
| GPIO18 / 19 | USB D− / D+ |
| GPIO20 / 21 | Debug UART RX / TX (test pads) |

### Bill of materials

| Ref | Qty | Part | MPN (or spec) | Notes |
|---|---|---|---|---|
| U1 | 1 | ESP32-C3-MINI-1U, 4 MB | ESP32-C3-MINI-1U-N4 | u.FL antenna |
| U2 | 1 | 3.3 V LDO 600 mA | AP2112K-3.3TRG1 | SOT-23-5 |
| U3 | 1 | Schmitt buffer, 5 V tolerant | SN74LVC1G17DBVR | SOT-23-5 |
| U4 | 1 | USB ESD array | USBLC6-2SC6 | SOT-23-6 |
| U5 | 1 | Hall switch, omnipolar | TI DRV5032 (pick variant) | SOT-23 |
| J1 | 1 | USB-C receptacle | GCT USB4105-GF-A | USB 2.0 |
| J2 | 1 | 3-pin latching header | JST BM03B-GHS-TBT | Sensor harness |
| D1, D2 | 2 | 5 V TVS | SMF5.0A | VBUS, sensor signal |
| F1 | 1 | PTC 500 mA hold | Bourns MF-MSMF050-2 | Board supply |
| F2 | 1 | PTC ~100 mA hold | Bourns MF-PSMF010X-2 | Sensor supply |
| LED1 | 1 | RGB LED, common anode | PLCC-4 (pick stocked part) | Under light pipe |
| Q1–Q3 | 3 | N-MOSFET | 2N7002 | LED switches |
| SW1, SW2 | 2 | Tactile switch | SMD, top side | RESET, BOOT |
| JP1 | 1 | 3-pad solder jumper | Footprint only | NPN / PNP |
| R, C | — | Passives | 0603 | Values in sections above |

Off-board: M8 3-pin female panel socket with leads (IP67), GH housing GHR-03V-S + SSHL-002T-P0.2 contacts, u.FL→RP-SMA bulkhead pigtail, IP67 2.4 GHz antenna, enclosure, cable gland or IP67 USB-C pass-through, light pipe, magnet.

### PCB layout

- 2 layers, 1.6 mm, 1 oz copper, ENIG finish (flat pads for the module), all parts on the top side, about 45 × 35 mm, four M3 holes.
- Ground pour on both layers, stitched with vias.
- TVS and ESD parts right at their connectors, with short ground returns.
- USB D+/D− as a short 90 Ω pair, away from the sensor input.
- USB-C on a board edge, reachable by a gland cable or an IP67 pass-through.
- LED under the light-pipe position; Hall sensor where the board is closest to the lid.
- Silkscreen: `NPN | PNP` at JP1, M8 pin colours at J2, a blank box for the board's label.

### Ordering from PCBWay

- Export from KiCad: Gerbers, drill files, BOM CSV (designator, qty, manufacturer, MPN, description), and the top-side placement file. PCBWay's plugin in KiCad's Plugin and Content Manager can generate these in one step.
- First order: 5 assembled prototypes. After bench and side-by-side testing, about 15.
- Approve any part substitutions PCBWay proposes, especially the module and LDO.
- Flash firmware yourself over USB.

## Firmware

PlatformIO, Arduino framework (ESP32-C3), 4 MB partition table with two app slots plus a LittleFS data partition. JSON with ArduinoJson; the setup page uses the built-in `WebServer` and `DNSServer`.

### Parts

| Part | Job |
|---|---|
| Settings | Stored in the ESP32's preferences storage: WiFi SSID/password, head ID, head name, API URL, device token, work start/end, sync interval, sensor type (NPN/PNP), time zone (default `EST5EDT,M3.2.0,M11.1.0`), configured flag. |
| Counter | Interrupt on the sensor-type edge; ignores pulses under the minimum width; count read atomically. |
| Clock | Network time (SNTP). Before time is known, readings carry time-since-boot and are converted once time is set. |
| Buffer | Queue in LittleFS: append, read oldest N, drop oldest N, prune older than 7 days, survives restarts, holds at least 10,080 entries (a week of minutes). |
| Reporter | Port of `connect_client.py`: up to 500 oldest readings per report, heartbeat when empty, boot flag on first report, same 200 / 401 / 403 / 422 / unreachable handling. Adds `rssi` and `fw` to each report. |
| WiFi | Power-save off, auto-reconnect with back-off (1 s up to 60 s), radio restart after repeated failure, join the strongest access point for the SSID. Never enters setup mode on its own. |
| Setup mode | Setup network and config page (below). |
| Status LED | Board state to colour and blink pattern. |
| Watchdog | Restarts the board if the program stalls for 30 s. |

Work hours behave as today: outside them, counts accumulate and go out as one reading at the first report of the day.

### Report format

```
POST {API_URL}/heading/headers/{HEAD_ID}/telemetry
X-Device-Token: {DEVICE_TOKEN}
{"readings":[{"at":"2026-10-09T10:22:00-04:00","count":64}],
 "ip":"192.168.1.78","boot":false,"rssi":-61,"fw":"1.0.0"}
```

### Setup mode

- Entered on first boot (not configured), by holding the magnet on the lid for 5 s, or by holding BOOT for 5 s.
- Network `piSensor-Setup-XXXX` (last four of the MAC), WPA2 with one shared setup password compiled into the firmware.
- The config page opens automatically (captive portal); fallback `http://192.168.4.1`.
- Page: WiFi network picker with signal strength (or manual entry) and password; head name, head ID, API URL (prefilled), device token (write-only, blank keeps the current one), work start/end, sync interval, sensor type. Footer: firmware version, MAC.
- Validation: head ID > 0; work start < work end, both 0–23; sync interval 1–60 min; API URL starts with `http://` or `https://`.
- **Test & Save:** joins the plant WiFi while the setup network stays up, sends one heartbeat to Connect, and shows the result (network, IP, signal, Connect reachable, token accepted). Only a passing test saves and restarts into run mode. A failure says why and saves nothing.
- If already configured and the page is idle for 10 minutes, return to run mode with the old settings.
- Counting continues throughout setup mode.

### Failure handling

| Event | Behaviour | LED |
|---|---|---|
| Plant WiFi drops | Keep counting into the buffer; reconnect with back-off; restart radio and rescan after repeated failures | Fast yellow |
| Connect unreachable or 5xx | Keep counts; retry next interval; backlog drains 500 per report; server skips duplicates | Solid amber |
| Token rejected (401/403) | Keep counts; fix through setup mode | Red blink |
| 422 | Drop only the readings Connect named | — |
| Time unknown after restart | Stamp by time-since-boot; send nothing until time is known | — |
| Firmware stall | Watchdog restart; buffer intact; boot flag on next report | — |
| Power loss | Resume with buffer intact | — |
| Setup test fails | Save nothing; show reason; keep old settings | Blue |

Logs go to USB serial only. In the field, Connect shows trouble: weak RSSI, a gap since the last heartbeat, or an unexpected boot flag.

## Connect changes

Accept two optional fields in the telemetry body, `rssi` (integer dBm) and `fw` (string), and store them with the header. No other API change.

## Testing and bring-up

1. Logic tests on the laptop (PlatformIO native): buffer, reporter response handling against a fake Connect, work hours, pre-time-sync timestamps, pulse filter.
2. Bench, on the 5 prototypes: USB flash; full setup flow from a phone; NPN and PNP sensors via JP1; unplug and restore the router and confirm the backlog drains with no duplicate counts; wrong token → red, then fixed; magnet through the real lid.
3. Side by side: one board next to its Pi on a machine for a week, reporting to a test header ID in Connect; compare minute counts.
4. Signal survey: run setup at all 11 machines, record signal strength, move antennas where weak.
5. Order the batch of about 15.

## Open items

1. Firmware update delivery: USB only, upload page, Connect-hosted pull, or upload page plus Connect. Partitions are ready for any of them.
2. Power entry: cable gland with the cable attached inside, or an IP67 USB-C pass-through. A USB-C plug may not pass through a small gland; choose a gland that fits the plug or a split cable entry.
3. Enclosure: polycarbonate IP67 box (for example a Hammond 1554 with a clear lid), how it mounts to the machine, and a breather vent if condensation shows up.
4. Pick the exact RGB LED, DRV5032 variant, M8 panel socket, pigtail and antenna from stocked parts.
5. Minimum real stud pulse width: measure on a machine with a logic analyser, then set the noise filter.
6. Value of the shared setup password.
7. Check how Connect validates the telemetry body so `rssi` and `fw` are accepted.
8. Time source: confirm the plant network reaches a public NTP server; if not, point the board at a local one.
