# Raspberry Pi Sensor System 2.0 Setup Guide

This guide will walk you through setting up the Sensor System 2.0 on a brand new Raspberry Pi Zero W2 with the Waveshare 1.3" OLED HAT.

## Hardware Requirements
- Raspberry Pi Zero W2
- Waveshare 1.3" OLED Display HAT (128x64)
- MicroSD card (64GB recommended)
- Inductive sensor connected to GPIO pin 17
- Power supply

## Step 1: Raspberry Pi OS Installation

1. **Download Raspberry Pi Imager** from https://www.raspberrypi.org/software/
2. **Flash Raspberry Pi OS Lite** (64-bit) to your SD card
3. **Enable SSH and WiFi** before first boot:
   - Create `ssh` file in boot partition (empty file, no extension)
   - Create `wpa_supplicant.conf` in boot partition with your WiFi credentials:
   ```
   country=US
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1
   
   network={
       ssid="YOUR_WIFI_NAME"
       psk="YOUR_WIFI_PASSWORD"
   }
   ```

## Step 2: Initial Pi Setup

1. **Boot the Pi** and find its IP address (check your router or use `nmap`)
2. **SSH into the Pi**:
   ```bash
   ssh pi@192.168.1.XXX
   ```
3. **Update the system**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
4. **Enable required interfaces**:
   ```bash
   sudo raspi-config
   ```
   - Navigate to "Interface Options"
   - Enable SPI (for OLED display)
   - Enable I2C (backup communication method)
   - Enable GPIO
   - Finish and reboot

## Step 3: Run the Automated Setup Script

The easiest way is to run our automated setup script:

```bash
curl -sSL https://raw.githubusercontent.com/gagesmith3/piSensor/main/setup_sensor_v2.sh | bash
```

**OR** follow the manual steps below if you prefer to do it step by step.

## Manual Setup Steps

### Install Python Dependencies
```bash
# Install Python 3 and pip if not already installed
sudo apt install python3 python3-pip python3-venv -y

# Install system dependencies for display libraries
sudo apt install python3-dev python3-pil python3-numpy -y
sudo apt install libfreetype6-dev libjpeg-dev libopenjp2-7 libtiff5 -y

# Install GPIO library
sudo apt install python3-rpi.gpio -y
```

### Create Project Directory
```bash
# Create project directory
mkdir -p /home/pi/sensor_system
cd /home/pi/sensor_system

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate
```

### Install Python Packages
```bash
# Install required packages
pip install --upgrade pip
pip install mysql-connector-python
pip install schedule
pip install luma.oled
pip install pillow
```

### Download Sensor Code
```bash
# Download the sensor system files
wget https://raw.githubusercontent.com/gagesmith3/piSensor/main/sensor_v2.py
chmod +x sensor_v2.py
```

### Configure the System
```bash
# Copy and edit the configuration
cp sensor_v2.py sensor_v2_config.py
nano sensor_v2_config.py
```

Update the configuration section at the bottom of the file:
```python
config = {
    'head_name': 'YOUR_HEADER_NAME',  # e.g., 'NATIONAL_1'
    'sensor_pin': 17,  # GPIO pin for inductive sensor
    'database': {
        'host': '192.168.1.54',  # Your database server IP
        'user': 'webapp',
        'password': 'STUDS2650',
        'database': 'iwt_db'
    }
}
```

### Create Systemd Service (Auto-start on boot)
```bash
sudo nano /etc/systemd/system/sensor-system.service
```

Add this content:
```ini
[Unit]
Description=Sensor System 2.0
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/sensor_system
Environment=PATH=/home/pi/sensor_system/venv/bin
ExecStart=/home/pi/sensor_system/venv/bin/python sensor_v2.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sensor-system.service
sudo systemctl start sensor-system.service
```

## Step 4: Hardware Setup

### Waveshare HAT Connection
1. **Power off the Pi** completely
2. **Attach the Waveshare 1.3" OLED HAT** to the GPIO header
3. **Connect your inductive sensor** to GPIO pin 17 and ground
4. **Power on the Pi**

### Verify HAT Installation
```bash
# Check if SPI is working
ls /dev/spi*
# Should show: /dev/spidev0.0  /dev/spidev0.1

# Test I2C (if using I2C mode)
sudo i2cdetect -y 1
```

## Step 5: Testing and Verification

### Check Service Status
```bash
# Check if service is running
sudo systemctl status sensor-system.service

# View logs
sudo journalctl -u sensor-system.service -f
```

### Manual Testing
```bash
cd /home/pi/sensor_system
source venv/bin/activate
python sensor_v2.py
```

### Test Database Connection
```bash
# Test database connectivity
python3 -c "
import mysql.connector
try:
    conn = mysql.connector.connect(
        host='192.168.1.54',
        user='webapp', 
        password='STUDS2650',
        database='iwt_db'
    )
    print('Database connection successful!')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

## Troubleshooting

### Common Issues

1. **Display not working**:
   ```bash
   # Check SPI is enabled
   sudo raspi-config
   # Interface Options -> SPI -> Enable
   ```

2. **Permission errors**:
   ```bash
   # Add pi user to gpio group
   sudo usermod -a -G gpio pi
   sudo usermod -a -G spi pi
   ```

3. **Database connection fails**:
   - Check network connectivity: `ping 192.168.1.54`
   - Verify database server is running
   - Check firewall settings on database server

4. **Service won't start**:
   ```bash
   # Check logs for errors
   sudo journalctl -u sensor-system.service -n 50
   
   # Check Python path and permissions
   which python3
   ls -la /home/pi/sensor_system/
   ```

### View System Logs
```bash
# Real-time logs
sudo journalctl -u sensor-system.service -f

# Recent logs
sudo journalctl -u sensor-system.service -n 100

# Logs since last boot
sudo journalctl -u sensor-system.service -b
```

## Configuration Options

### Database Settings
Update `/home/pi/sensor_system/sensor_v2.py` configuration:
- `head_name`: Your specific header identifier
- `sensor_pin`: GPIO pin for inductive sensor (default: 17)
- Database connection details

### GPIO Pin Mapping for Waveshare HAT
The code includes default pin mappings, but verify with your specific HAT model:
- Buttons: GPIO 21, 20, 16
- Joystick: GPIO 6, 19, 5, 26, 13

## Maintenance

### Update the System
```bash
cd /home/pi/sensor_system
git pull  # If using git
sudo systemctl restart sensor-system.service
```

### Backup Configuration
```bash
# Backup your configuration
cp sensor_v2.py sensor_v2_backup_$(date +%Y%m%d).py
```

### Monitor System Health
```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check temperature
vcgencmd measure_temp
```

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review system logs: `sudo journalctl -u sensor-system.service -f`
3. Test individual components (database, display, sensor)
4. Verify hardware connections