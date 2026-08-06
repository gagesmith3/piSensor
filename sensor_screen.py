#!/usr/bin/env python3
#version 1.0 - Waveshare OLED HAT Edition
"""
IWT Stud Sensor with Waveshare OLED Display
Production Hardened Sensor with Real-time Display
Monitors inductive sensor on GPIO and logs stud counts to database.
Includes error handling, connection management, logging, and OLED display feedback.
"""
import time
import logging
import logging.handlers
import RPi.GPIO as GPIO
import mysql.connector
from mysql.connector import Error as MySQLError
import schedule
import datetime
import os
from pathlib import Path
import socket
import threading
from PIL import Image, ImageDraw, ImageFont

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")
    print("Install with: pip install python-dotenv")

# Try to import display libraries
try:
    from luma.oled.device import ssd1306
    from luma.core.interface.serial import i2c
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False
    print("Warning: Luma OLED libraries not installed. Running in headless mode.")
    print("Install with: pip install luma.oled")

# ============================================================================
# CONFIGURATION - Set these values for your deployment
# ============================================================================
CONFIG = {
    'sensor_pin': int(os.getenv('SENSOR_PIN', '17')),
    'head_name': os.getenv('HEAD_NAME', 'HEADNAME'),
    'head_id': int(os.getenv('HEAD_ID', '0')),
    'database': {
        'host': os.getenv('DB_HOST', '192.168.1.6'),
        'user': os.getenv('DB_USER', 'webapp'),
        'password': os.getenv('DB_PASS', 'STUDS2650'),
        'database': os.getenv('DB_NAME', 'iwt_db'),
    },
    'work_hours': {
        'start': int(os.getenv('WORK_START', '7')),
        'end': int(os.getenv('WORK_END', '17')),
    },
    'sync_interval_minutes': int(os.getenv('SYNC_INTERVAL', '1')),
    'display': {
        'i2c_port': int(os.getenv('I2C_PORT', '1')),
        'i2c_address': int(os.getenv('I2C_ADDRESS', '0x3c'), 16),
    }
}



# ============================================================================
# LOGGING SETUP
# ============================================================================
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger('SensorScreen')
logger.setLevel(logging.DEBUG)

# File handler - rotating to prevent massive log files
file_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / 'sensor_screen.log',
    maxBytes=5*1024*1024,  # 5MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)

# Console handler for debugging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Format with timestamps
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ============================================================================
# DISPLAY MANAGER
# ============================================================================
class DisplayManager:
    """Manages OLED display rendering and updates."""
    
    def __init__(self, config):
        self.config = config
        self.device = None
        self.font_large = None
        self.font_small = None
        self.lock = threading.Lock()
        
        if DISPLAY_AVAILABLE:
            try:
                self.init_display()
            except Exception as e:
                logger.warning(f"Display initialization failed: {e}")
                self.device = None
        else:
            logger.info("Display libraries not available - text mode only")
    
    def init_display(self):
        """Initialize the OLED display via I2C."""
        try:
            serial = i2c(port=self.config['display']['i2c_port'], 
                        address=self.config['display']['i2c_address'])
            self.device = ssd1306(serial)
            logger.info(f"✓ Display initialized: {self.device.width}x{self.device.height}")
            
            # Load fonts
            try:
                self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            except:
                self.font_large = ImageFont.load_default()
            
            try:
                self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                self.font_small = ImageFont.load_default()
            
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
            self.device = None
    
    def draw_main_screen(self, count, db_connected, active, last_detection):
        """Draw main counter screen."""
        if not self.device:
            print(f"Count: {count} | DB: {'✓' if db_connected else '✗'}")
            return
        
        with self.lock:
            try:
                with Image.new("1", (self.device.width, self.device.height), "black") as image:
                    draw = ImageDraw.Draw(image)
                    
                    # Large count display (centered)
                    count_text = f"{count:,}"
                    bbox = draw.textbbox((0, 0), count_text, font=self.font_large)
                    text_width = bbox[2] - bbox[0]
                    text_x = (128 - text_width) // 2
                    text_y = (64 - (bbox[3] - bbox[1])) // 2
                    draw.text((text_x, text_y), count_text, font=self.font_large, fill="white")
                    
                    # DB status indicator (bottom right)
                    status_symbol = "✓" if db_connected else "✗"
                    draw.text((110, 55), status_symbol, font=self.font_small, fill="white")
                    
                    self.device.display(image)
            except Exception as e:
                logger.error(f"Display draw error: {e}")
    
    def draw_info_screen(self, head_name, head_id, ip_address, db_status):
        """Draw system info screen."""
        if not self.device:
            print(f"Header: {head_name} | IP: {ip_address} | DB: {db_status}")
            return
        
        with self.lock:
            try:
                with Image.new("1", (self.device.width, self.device.height), "black") as image:
                    draw = ImageDraw.Draw(image)
                    
                    # Title
                    draw.text((2, 2), "SYSTEM INFO", font=self.font_small, fill="white")
                    draw.line((0, 12, 127, 12), fill="white")
                    
                    # Info
                    draw.text((2, 16), f"Head: {head_name}", font=self.font_small, fill="white")
                    draw.text((2, 28), f"ID: {head_id}", font=self.font_small, fill="white")
                    draw.text((2, 40), f"IP: {ip_address}", font=self.font_small, fill="white")
                    draw.text((2, 52), f"DB: {db_status}", font=self.font_small, fill="white")
                    
                    self.device.display(image)
            except Exception as e:
                logger.error(f"Display draw error: {e}")
# ============================================================================
# SENSOR STATE CLASS
# ============================================================================
class SensorState:
    """Manages sensor state and database connection."""
    
    def __init__(self, config):
        self.config = config
        self.gpio_pin = config['sensor_pin']
        self.head_name = config['head_name']
        self.head_id = config['head_id']
        
        # Sensor state
        self.count = 0
        self.old_state = 2  # Impossible initial state
        self.last_detection_time = None
        
        # Database connection
        self.db_connection = None
        self.last_sync_time = None
        self.sync_failures = 0
        self.max_retry_failures = 5
        
        # Display
        self.display = DisplayManager(config)
        
        logger.info(f"Sensor initialized for {self.head_name} on pin {self.gpio_pin}")
    
    def init_gpio(self):
        """Initialize GPIO pins with error handling."""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            logger.info(f"✓ GPIO initialized on pin {self.gpio_pin}")
            return True
        except Exception as e:
            logger.error(f"✗ GPIO initialization failed: {e}")
            return False
    
    def get_local_ip(self):
        """Get the Pi's local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            logger.debug(f"Local IP detected: {ip}")
            return ip
        except Exception as e:
            logger.warning(f"Could not determine local IP: {e}")
            return "N/A"
    
    def connect_db(self):
        """Establish database connection with error handling."""
        try:
            self.db_connection = mysql.connector.connect(
                host=self.config['database']['host'],
                user=self.config['database']['user'],
                password=self.config['database']['password'],
                database=self.config['database']['database'],
                autocommit=True,
                connection_timeout=5
            )
            logger.info(f"✓ Database connected to {self.config['database']['host']}")
            self.sync_failures = 0
            return True
        except MySQLError as e:
            logger.error(f"✗ Database connection failed: {e}")
            self.db_connection = None
            return False
    
    def is_db_connected(self):
        """Check if database connection is still alive."""
        if not self.db_connection:
            return False
        try:
            self.db_connection.ping(reconnect=True)
            return True
        except MySQLError:
            logger.warning("Database connection lost, will reconnect...")
            self.db_connection = None
            return False
    
    def detect_metal(self):
        """Read sensor and increment count on detection."""
        try:
            new_state = GPIO.input(self.gpio_pin)
            
            # Rising edge detection (transition from 0 to 1)
            if new_state != self.old_state:
                if new_state == 1:
                    self.count += 1
                    self.last_detection_time = datetime.datetime.now()
                    logger.debug(f"Metal detected - Count: {self.count}")
                self.old_state = new_state
        except Exception as e:
            logger.error(f"✗ Error reading sensor: {e}")
    
    def sync_data(self):
        """Upload count data to database with error handling."""
        # Skip sync outside work hours
        now = datetime.datetime.now()
        if not (self.config['work_hours']['start'] <= now.hour < self.config['work_hours']['end']):
            logger.debug(f"Outside work hours ({now.hour}:00) - skipping sync")
            return False
        
        # Reconnect if needed
        if not self.is_db_connected():
            logger.info("Attempting database reconnection...")
            if not self.connect_db():
                self.sync_failures += 1
                if self.sync_failures >= self.max_retry_failures:
                    logger.critical(f"Database unreachable for {self.sync_failures} attempts!")
                return False
        
        try:
            cursor = self.db_connection.cursor()
            
            # Get current IP address
            pi_ip = self.get_local_ip()
            
            # Insert count record (only if we have counts)
            if self.count > 0:
                # updateDate was dropped from the schema. It stored a locale
                # MM/DD/YY string that sorted lexically rather than by date,
                # and it was fully derivable from updateFullDate anyway.
                insert_query = """
                    INSERT INTO heading_rates
                    (headName, studCount, updateFullDate, updateHour, updateMinute)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    self.head_name,
                    self.count,
                    now,
                    now.hour,
                    now.minute
                )
                cursor.execute(insert_query, values)
            
            # Update machine status, IP address, and heartbeat timestamp (always)
            status = 'ACTIVE' if self.count > 0 else 'INACTIVE'
            update_query = """UPDATE heading_data 
                             SET headStatus = %s, headerIP = %s, lastHeartbeat = %s 
                             WHERE headID = %s"""
            cursor.execute(update_query, (status, pi_ip, now, self.head_id))
            
            cursor.close()
            
            # Reset count after successful sync
            logged_count = self.count
            self.count = 0
            self.last_sync_time = now
            self.sync_failures = 0
            
            if logged_count > 0:
                logger.info(f"✓ Synced {logged_count} counts at {now.strftime('%H:%M:%S')} (IP: {pi_ip})")
            else:
                logger.debug(f"✓ Heartbeat update at {now.strftime('%H:%M:%S')} (IP: {pi_ip})")
            return True
            
        except MySQLError as e:
            self.sync_failures += 1
            logger.error(f"✗ Database sync failed (attempt {self.sync_failures}): {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected sync error: {e}")
            return False
    
    def init_startup(self):
        """Initialize database alarm on startup."""
        try:
            if not self.is_db_connected():
                if not self.connect_db():
                    logger.warning("Could not connect to DB for startup init")
                    return
            
            cursor = self.db_connection.cursor()
            cursor.execute(
                "UPDATE heading_data SET headerAlarm = 'FALSE' WHERE headID = %s",
                (self.head_id,)
            )
            cursor.close()
            logger.info("✓ Startup initialization complete")
        except MySQLError as e:
            logger.error(f"✗ Startup init failed: {e}")
    
    def update_display(self):
        """Update the OLED display."""
        self.display.draw_main_screen(
            self.count,
            self.is_db_connected(),
            self.count > 0,
            self.last_detection_time
        )
    
    def cleanup(self):
        """Clean shutdown."""
        try:
            if self.db_connection:
                self.db_connection.close()
            GPIO.cleanup()
            logger.info("✓ Cleanup complete")
        except Exception as e:
            logger.error(f"✗ Cleanup error: {e}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    logger.info("=" * 60)
    logger.info("IWT Stud Sensor with Waveshare OLED Display v1.0 Starting")
    logger.info("=" * 60)
    
    sensor = SensorState(CONFIG)
    
    # Initialize GPIO
    if not sensor.init_gpio():
        logger.critical("Failed to initialize GPIO - exiting")
        return
    
    # Connect to database
    if not sensor.connect_db():
        logger.warning("Starting without database connection - will retry")
    
    # Initialize startup state
    sensor.init_startup()
    
    # Schedule data sync every N minutes
    schedule.every(CONFIG['sync_interval_minutes']).minutes.do(sensor.sync_data)
    
    # Display update every 0.5 seconds
    last_display_update = time.time()
    display_interval = 0.5
    
    logger.info("Entering detection loop...")
    
    try:
        while True:
            # Sensor detection (fast)
            sensor.detect_metal()
            
            # Scheduled tasks
            schedule.run_pending()
            
            # Display updates (every 0.5s)
            now = time.time()
            if now - last_display_update >= display_interval:
                sensor.update_display()
                last_display_update = now
            
            time.sleep(0.01)  # Small delay to prevent CPU spinning
    
    except KeyboardInterrupt:
        logger.info("Shutdown signal received (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Unexpected error in main loop: {e}", exc_info=True)
    finally:
        sensor.cleanup()
        logger.info("Sensor stopped")

if __name__ == '__main__':
    main()
