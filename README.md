# piSensor - IWT Stud Sensor Counter

Metal sensing application that monitors an inductive sensor on a Raspberry Pi and logs stud counts to a MySQL database.

## Features

- Real-time metal detection on GPIO
- Automatic count logging to database
- IP address tracking for sensor location
- Heartbeat monitoring for sensor health
- Rotating logs with configurable verbosity
- Work-hour based data sync
- Automatic database reconnection with retry logic

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
SENSOR_PIN=17              # GPIO pin (BCM numbering)
HEAD_NAME=NATIONAL_1       # Heading identifier
HEAD_ID=1                  # Database heading ID
DB_HOST=192.168.1.54       # MySQL host
DB_USER=webapp             # Database user
DB_PASS=password           # Database password
DB_NAME=iwt_db             # Database name
WORK_START=7               # Work hours start (7 AM)
WORK_END=17                # Work hours end (5 PM)
SYNC_INTERVAL=1            # Sync interval (minutes)
```

## Files

- **sensor.py** - Main sensor monitoring application
- **sensor_v2.py** - Alternative sensor implementation
- **sensor_counter_v2.py** - Counter variant
- **.env.example** - Configuration template
- **setup.sh** - Automated setup script
- **requirements.txt** - Python dependencies

## Database Tables

- `heading_data` - Machine status and configuration
- `heading_rates` - Count history records

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

**Permission denied on /var/log/sensor:**
- The script now logs locally in `./logs/` directory

**Virtual environment not activating:**
```bash
bash setup.sh  # Recreate venv
source venv/bin/activate
```

**Database connection failed:**
- Check `.env` configuration
- Verify database host is reachable: `ping 192.168.1.54`
- Check MySQL credentials