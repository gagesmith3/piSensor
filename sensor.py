#version 4.0 - Reports through the Connect API
"""
IWT Stud Sensor - Headless Counter
Monitors the inductive sensor on GPIO and reports stud counts to Connect.

v4.0: the sensor no longer writes the database. Each sync interval it hands the
count to connect_client.Reporter, which buffers it locally and posts it to
connectCoreAPI (POST /heading/headers/{HEAD_ID}/telemetry). The server records
the reading, the header's status and heartbeat, and puts a paused lot back to
work when counts arrive. Counts survive an API outage or a reboot in the buffer.
"""
import time
import logging
import logging.handlers
import RPi.GPIO as GPIO
import schedule
import datetime
import os
from pathlib import Path

from connect_client import ConnectClient, ReadingBuffer, Reporter

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")
    print("Install with: pip install python-dotenv")

# ============================================================================
# CONFIGURATION - Set these values for your deployment (in .env)
# ============================================================================
CONFIG = {
    'sensor_pin': int(os.getenv('SENSOR_PIN', '17')),
    'head_name': os.getenv('HEAD_NAME', 'HEADNAME'),
    'head_id': int(os.getenv('HEAD_ID', '0')),
    'api_url': os.getenv('API_URL', 'http://192.168.1.6:9090/api/v1'),
    'device_token': os.getenv('DEVICE_TOKEN', ''),
    'work_hours': {
        'start': int(os.getenv('WORK_START', '7')),
        'end': int(os.getenv('WORK_END', '17')),
    },
    'sync_interval_minutes': int(os.getenv('SYNC_INTERVAL', '1')),
}

# ============================================================================
# LOGGING SETUP
# ============================================================================
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / 'logs'
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
    """Counts studs and hands each interval's count to the reporter."""

    def __init__(self, config, reporter):
        self.config = config
        self.gpio_pin = config['sensor_pin']
        self.head_name = config['head_name']
        self.head_id = config['head_id']
        self.reporter = reporter

        # Sensor state
        self.count = 0
        self.old_state = 2  # Impossible initial state
        self.last_detection_time = None

        logger.info(f"Sensor initialized for {self.head_name} (headID {self.head_id}) on pin {self.gpio_pin}")

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
        """Report this interval's count to Connect.

        Outside work hours nothing is sent and the count keeps accumulating,
        as before v4: the first sync of the day reports it as one reading.
        The count moves into the reporter's buffer before anything is sent,
        so a failed report loses nothing and a retried one counts nothing twice.
        """
        now = datetime.datetime.now()
        if not (self.config['work_hours']['start'] <= now.hour < self.config['work_hours']['end']):
            logger.debug(f"Outside work hours ({now.hour}:00) - skipping sync")
            return False

        count, self.count = self.count, 0

        try:
            return self.reporter.report(count)
        except Exception as e:
            logger.error(f"✗ Unexpected sync error: {e}", exc_info=True)
            return False

    def cleanup(self):
        """Clean shutdown."""
        try:
            GPIO.cleanup()
            logger.info("✓ Cleanup complete")
        except Exception as e:
            logger.error(f"✗ Cleanup error: {e}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    logger.info("=" * 60)
    logger.info("IWT Stud Sensor v4.0 Starting (reports through the Connect API)")
    logger.info("=" * 60)

    if not CONFIG['device_token']:
        logger.critical("DEVICE_TOKEN is not set in .env - Connect will refuse every report; counts will be buffered")

    reporter = Reporter(
        ConnectClient(CONFIG['api_url'], CONFIG['head_id'], CONFIG['device_token']),
        ReadingBuffer(BASE_DIR / 'buffer.db'),
        logger,
    )
    sensor = SensorState(CONFIG, reporter)

    # Initialize GPIO
    if not sensor.init_gpio():
        logger.critical("Failed to initialize GPIO - exiting")
        return

    logger.info(f"Reporting to {CONFIG['api_url']}")

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
        reporter.buffer.close()
        logger.info("Sensor stopped")

if __name__ == '__main__':
    main()
