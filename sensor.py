#version 3.2 - Production Hardened
"""
IWT Stud Sensor - Headless Counter
Monitors inductive sensor on GPIO and logs stud counts to database.
Includes error handling, connection management, and logging.
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

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")
    print("Install with: pip install python-dotenv")

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
}

# ============================================================================
# LOGGING SETUP
# ============================================================================
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger('SensorCounter')
logger.setLevel(logging.DEBUG)

# File handler - rotating to prevent massive log files
file_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / 'sensor.log',
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
        
        logger.info(f"Sensor initialized for {self.head_name} on pin {self.gpio_pin}")
    
    def init_gpio(self):
        """Initialize GPIO pin with error handling."""
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
            # Connect to an external address (doesn't actually send data)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            logger.debug(f"Local IP detected: {ip}")
            return ip
        except Exception as e:
            logger.warning(f"Could not determine local IP: {e}")
            return None
    
    def connect_db(self):
        """Establish database connection with error handling."""
        try:
            self.db_connection = mysql.connector.connect(
                host=self.config['database']['host'],
                user=self.config['database']['user'],
                password=self.config['database']['password'],
                database=self.config['database']['database'],
                autocommit=True,  # Auto-commit queries
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
    logger.info("IWT Stud Sensor v3.2 Starting")
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
    
    logger.info("Entering detection loop...")
    
    try:
        while True:
            sensor.detect_metal()
            schedule.run_pending()
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
