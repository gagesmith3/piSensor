# piSensor - IWT Stud Sensor Counter

Metal sensing application that monitors an inductive sensor on a Raspberry Pi and reports stud counts to Connect (connectCoreAPI).

**v4 (2026-10-09): the sensor no longer writes the database.** It posts each minute's count to `POST /api/v1/heading/headers/{HEAD_ID}/telemetry` with its device token, and the server records the reading, the header's status and heartbeat, and puts a paused lot back to work when counts arrive. The sensor holds no database credential.

## Features

- Real-time metal detection on GPIO
- Counts reported to Connect once a minute, with the Pi's IP and a heartbeat
- **Offline buffer** (`buffer.db`, SQLite): a count stays on the Pi until Connect acknowledges it, survives a reboot, and is resent after an outage (kept up to 7 days). The server skips a reading it already has, so a resend never counts twice.
- Rotating logs
- Work-hour based sync: outside work hours counts accumulate and are reported at the first sync of the day
- Standard library only for the Connect client - updating a Pi is `git pull` and a restart

## Quick Start

### First Time Setup

```bash
git clone https://github.com/gagesmith3/piSensor.git
cd piSensor
bash setup.sh          # Creates .env and virtual environment
nano .env              # Edit with your configuration
source venv/bin/activate
python3 sensor.py
```

### Configuration

Edit `.env` with your specific values:

```env
SENSOR_PIN=17                              # GPIO pin (BCM numbering)
HEAD_NAME=NATIONAL_1                       # Heading identifier (logs and screen)
HEAD_ID=1                                  # heading_data.headID - the header this Pi reports as
API_URL=http://192.168.1.6:9090/api/v1     # connectCoreAPI
DEVICE_TOKEN=                              # this header's token (see below) - a credential
WORK_START=7                               # Work hours start (7 AM)
WORK_END=17                                # Work hours end (5 PM)
SYNC_INTERVAL=1                            # Report interval (minutes)
```

The device token is issued on the Connect server, one per header:

```
E:\laragon\bin\php\php-8.3.30-Win32-vs16-x64\php.exe bin/issue-header-token.php <HEAD_ID>
```

It is printed once and only its hash is stored. Issuing a new one revokes the old, so do it only as part of updating that Pi. **Never commit `.env`.**

## Files

- **sensor.py** - Main sensor monitoring application (headless)
- **sensor_screen.py** - The same, with the Waveshare OLED display
- **connect_client.py** - The Connect API client, offline buffer and report step both scripts share
- **.env.example** - Configuration template
- **setup.sh** - Automated setup script
- **requirements.txt** - Python dependencies

## What the server writes

The API writes what the sensor used to write directly, on its behalf:

- `heading_rates` - one row per reporting minute with studs counted
- `heading_data` - `headStatus` (ACTIVE when the latest minute counted), `headerIP`, `lastHeartbeat` (the server's clock), and `headerAlarm = 'FALSE'` on the first report after a boot
- the header's lot, if it is PAUSED and studs are counted 5+ minutes after the pause: heading back to PROCESSING

## Logs

Logs are stored in `./logs/sensor.log` (rotating, max 5MB per file).

View live logs:
```bash
tail -f logs/sensor.log
```

## Running as a Service

To run sensor.py automatically at boot, add to crontab:

```bash
crontab -e
```

Add:
```cron
@reboot cd /path/to/piSensor && source venv/bin/activate && python3 sensor.py >> logs/cron.log 2>&1
```

## Troubleshooting

**"Connect refused the device token":**
- `DEVICE_TOKEN` in `.env` is missing, mistyped, or was replaced by a newer one. Issue a new token for this `HEAD_ID` and put it in `.env`. Counts are kept in the buffer meanwhile.

**"Connect unreachable":**
- Check `API_URL` and that the server is up: `curl http://192.168.1.6:9090/api/v1/health`
- Counts are buffered and sent when it is back.

**Permission denied on /var/log/sensor:**
- The script logs locally in `./logs/` directory

**Virtual environment not activating:**
```bash
bash setup.sh  # Recreate venv
source venv/bin/activate
```
