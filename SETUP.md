# IWT Stud Sensor - Setup & Deployment Guide

## Quick Start

### 1. Install Dependencies
```bash
# Navigate to piSensor directory
cd /path/to/piSensor

# Install Python packages
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy the example configuration
cp .env.example .env

# Edit with your specific settings
nano .env
```

### Configuration Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `SENSOR_PIN` | `17` | GPIO pin for inductive sensor (BCM) |
| `HEAD_NAME` | `NATIONAL_1` | Machine identifier |
| `HEAD_ID` | `1` | `heading_data.headID` - the header this Pi reports as |
| `API_URL` | `http://192.168.1.6:9090/api/v1` | connectCoreAPI base URL |
| `DEVICE_TOKEN` | *(issued per header)* | This header's token - `bin/issue-header-token.php <HEAD_ID>` on the Connect server. A credential: never commit it |
| `WORK_START` | `7` | Work day start hour (24-hour) |
| `WORK_END` | `17` | Work day end hour (24-hour) |
| `SYNC_INTERVAL` | `1` | Minutes between reports to Connect |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### 3. Test the Sensor
```bash
# Run in foreground for testing
python3 sensor.py

# You should see:
# ============================================================
# IWT Stud Sensor v4.0 Starting (reports through the Connect API)
# ============================================================
# ✓ GPIO initialized on pin 17
# Reporting to http://192.168.1.6:9090/api/v1
# Entering detection loop...
# ✓ Synced 64 counts in 1 readings (1 new, 0 already had)   <- once a minute
```

### 4. Deploy as systemd Service

Create `/etc/systemd/system/stud-sensor.service`:

```ini
[Unit]
Description=IWT Stud Sensor Counter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/piSensor
EnvironmentFile=/home/pi/piSensor/.env
ExecStart=/usr/bin/python3 /home/pi/piSensor/sensor.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable stud-sensor.service
sudo systemctl start stud-sensor.service
```

Check status:
```bash
sudo systemctl status stud-sensor.service
sudo journalctl -u stud-sensor.service -f  # Follow logs
```

### 5. Monitoring Logs

Logs are stored at `/var/log/sensor/sensor.log` (or home directory if no write access):

```bash
# View recent logs
tail -f /var/log/sensor/sensor.log

# Search for errors
grep ERROR /var/log/sensor/sensor.log

# View report history
grep -E "Synced|Connect" /var/log/sensor/sensor.log
```

## Troubleshooting

### Issue: "Connect unreachable"
- Check network connectivity: `ping 192.168.1.6`
- Check the API answers: `curl http://192.168.1.6:9090/api/v1/health`
- Counts are buffered in `buffer.db` and sent once it is back

### Issue: "Connect refused the device token"
- `DEVICE_TOKEN` in `.env` is missing, mistyped, or was replaced by a newer one
- Issue a new one for this `HEAD_ID` on the Connect server and put it in `.env`

### Issue: "GPIO initialization failed"
- Verify GPIO pin is correct in `.env`
- Run as root or add pi user to gpio group: `sudo usermod -a -G gpio pi`
- Reboot: `sudo reboot`

### Issue: "Permission denied" on log file
- Create directory: `sudo mkdir -p /var/log/sensor`
- Set permissions: `sudo chown pi:pi /var/log/sensor`

### Issue: Sensor not detecting
- Test GPIO pin: `python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print(GPIO.input(17))"`
- Verify inductive sensor is wired correctly
- Check GPIO pin number in `.env` matches hardware

## Production Checklist

- [ ] `.env` file created with correct credentials
- [ ] `.env` file is in `.gitignore` (never commit credentials)
- [ ] `requirements.txt` installed via pip
- [ ] Sensor tested in foreground mode
- [ ] Logs accessible at `/var/log/sensor/sensor.log`
- [ ] systemd service created and enabled
- [ ] Service restarts on boot
- [ ] Can reach the Connect API from the Pi (`curl $API_URL/health`)
- [ ] GPIO permissions set up correctly
- [ ] `DEVICE_TOKEN` issued for this header and set in `.env`

## Environment Variable Override

You can override `.env` settings via command line:

```bash
API_URL=http://192.168.1.100:9090/api/v1 python3 sensor.py
```

Or in systemd service, add to `[Service]` section:
```ini
Environment="API_URL=http://192.168.1.100:9090/api/v1"
```

## Security Notes

⚠️ **Never commit `.env` to git** - it contains this header's device token
- Use `.env.example` as template
- Add `.env` to `.gitignore` (already done)
- For git repositories, use environment variables in CI/CD systems
- A leaked token is revoked by issuing a new one for that header

## Uninstall

```bash
# Stop service
sudo systemctl stop stud-sensor.service
sudo systemctl disable stud-sensor.service

# Remove service file
sudo rm /etc/systemd/system/stud-sensor.service
sudo systemctl daemon-reload
```
