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
| `HEAD_ID` | `1` | Database machine ID |
| `DB_HOST` | `192.168.1.54` | MySQL server address |
| `DB_USER` | `webapp` | Database user |
| `DB_PASS` | `STUDS2650` | Database password |
| `DB_NAME` | `iwt_db` | Database name |
| `WORK_START` | `7` | Work day start hour (24-hour) |
| `WORK_END` | `17` | Work day end hour (24-hour) |
| `SYNC_INTERVAL` | `1` | Minutes between database syncs |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### 3. Test the Sensor
```bash
# Run in foreground for testing
python3 sensor.py

# You should see:
# ============================================================
# IWT Stud Sensor v3.2 Starting
# ============================================================
# ✓ GPIO initialized on pin 17
# ✓ Database connected to 192.168.1.54
# ✓ Startup initialization complete
# Entering detection loop...
```

### 4. Deploy as systemd Service

Create `/etc/systemd/system/stud-sensor.service`:

```ini
[Unit]
Description=IWT Stud Sensor Counter
After=network.target mysql.service
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

# View connection history
grep "Database" /var/log/sensor/sensor.log
```

## Troubleshooting

### Issue: "Database connection failed"
- Check network connectivity: `ping 192.168.1.54`
- Verify credentials in `.env`
- Check MySQL is running: `mysql -h 192.168.1.54 -u webapp -p`

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
- [ ] Can reach database from Pi
- [ ] GPIO permissions set up correctly
- [ ] Database tables exist (heading_rates, heading_data)

## Environment Variable Override

You can override `.env` settings via command line:

```bash
DB_HOST=192.168.1.100 python3 sensor.py
```

Or in systemd service, add to `[Service]` section:
```ini
Environment="DB_HOST=192.168.1.100"
```

## Security Notes

⚠️ **Never commit `.env` to git** - it contains database credentials
- Use `.env.example` as template
- Add `.env` to `.gitignore` (already done)
- For git repositories, use environment variables in CI/CD systems
- Rotate database password periodically

## Uninstall

```bash
# Stop service
sudo systemctl stop stud-sensor.service
sudo systemctl disable stud-sensor.service

# Remove service file
sudo rm /etc/systemd/system/stud-sensor.service
sudo systemctl daemon-reload
```
