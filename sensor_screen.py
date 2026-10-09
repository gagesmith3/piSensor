#!/usr/bin/env python3
#version 2.0 - Waveshare OLED HAT Edition, reports through the Connect API
"""
IWT Stud Sensor with Waveshare OLED Display
Monitors the inductive sensor on GPIO and reports stud counts to Connect, with
OLED display feedback.

v2.0: as sensor.py v4.0 - no database access. Counts are buffered locally and
posted to connectCoreAPI by connect_client.Reporter; the display's status mark
shows whether the last report was acknowledged.
"""
import time
import logging
import logging.handlers
import RPi.GPIO as GPIO
import schedule
import datetime
import os
from pathlib import Path
import threading
from PIL import Image, ImageDraw, ImageFont

from connect_client import ConnectClient, ReadingBuffer, Reporter, local_ip

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
    'api_url': os.getenv('API_URL', 'http://192.168.1.6:9090/api/v1'),
    'device_token': os.getenv('DEVICE_TOKEN', ''),
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
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / 'logs'
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
    
    def draw_main_screen(self, count, api_ok, active, last_detection):
        """Draw main counter screen."""
        if not self.device:
            print(f"Count: {count} | API: {'✓' if api_ok else '✗'}")
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
                    
                    # API status indicator (bottom right): the last report acknowledged
                    status_symbol = "✓" if api_ok else "✗"
                    draw.text((110, 55), status_symbol, font=self.font_small, fill="white")
                    
                    self.device.display(image)
            except Exception as e:
                logger.error(f"Display draw error: {e}")
    
    def draw_info_screen(self, head_name, head_id, ip_address, api_status):
        """Draw system info screen."""
        if not self.device:
            print(f"Header: {head_name} | IP: {ip_address} | API: {api_status}")
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
                    draw.text((2, 52), f"API: {api_status}", font=self.font_small, fill="white")
                    
                    self.device.display(image)
            except Exception as e:
                logger.error(f"Display draw error: {e}")
# ============================================================================
# SENSOR STATE CLASS
# ============================================================================
class SensorState:
    """Counts studs, hands each interval's count to the reporter, drives the display."""

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

        # Display
        self.display = DisplayManager(config)

        logger.info(f"Sensor initialized for {self.head_name} (headID {self.head_id}) on pin {self.gpio_pin}")

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
        """Report this interval's count to Connect - as sensor.py v4.0.

        Outside work hours nothing is sent and the count keeps accumulating.
        The count moves into the reporter's buffer before anything is sent, so
        a failed report loses nothing and a retried one counts nothing twice.
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

    def update_display(self):
        """Update the OLED display. The status mark is the last report's outcome -
        a flag, so the 0.5s redraw makes no network call."""
        self.display.draw_main_screen(
            self.count,
            self.reporter.api_ok,
            self.count > 0,
            self.last_detection_time
        )

    def show_info(self):
        """The system info screen, once at start."""
        self.display.draw_info_screen(
            self.head_name,
            self.head_id,
            local_ip() or "N/A",
            self.config['api_url'],
        )

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
    logger.info("IWT Stud Sensor with Waveshare OLED Display v2.0 Starting (Connect API)")
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
    sensor.show_info()

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
        reporter.buffer.close()
        logger.info("Sensor stopped")

if __name__ == '__main__':
    main()
