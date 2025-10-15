# Sensor System Version 2.0
# Features: OLED Display, Button Controls, Offline Data Queue, Multi-screen Interface
import time
import RPi.GPIO as GPIO
import mysql.connector
import sqlite3
import schedule
import datetime
import os
import json
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# Display and input libraries (will need to be installed)
# from luma.oled.device import ssd1306
# from luma.core.interface.serial import spi
# from luma.core.render import canvas
# from PIL import Image, ImageDraw, ImageFont

class DisplayScreen(Enum):
    """Available display screens that user can navigate through"""
    LIVE_COUNT = "live_count"
    UNCONFIRMED_TOTAL = "unconfirmed_total"  
    CONNECTION_STATUS = "connection_status"

class ConnectionStatus(Enum):
    """Database connection states"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

@dataclass
class CountRecord:
    """Structure for storing count data in offline queue"""
    timestamp: datetime.datetime
    count: int
    uploaded: bool = False
    retry_count: int = 0

@dataclass
class SystemState:
    """Current state of the sensor system"""
    # Live sensor data (current session)
    live_count: int = 0
    counting_paused: bool = False
    
    # Database sync state
    last_confirmed_count: int = 0      # From reqCount in database
    unconfirmed_count: int = 0         # From heading_rates sum since last confirm
    pending_upload_count: int = 0      # Local counts not yet uploaded
    
    # Connection and timing
    connection_status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    last_sync_time: Optional[datetime.datetime] = None
    last_detection_time: Optional[datetime.datetime] = None
    
    # UI state
    current_screen: DisplayScreen = DisplayScreen.LIVE_COUNT
    
    @property
    def total_unconfirmed_count(self) -> int:
        """Calculate total unconfirmed count including all sources"""
        return self.last_confirmed_count + self.unconfirmed_count + self.live_count + self.pending_upload_count

class DatabaseManager:
    """Handles all database operations with retry logic and connection monitoring"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        self.last_connection_attempt = None
        self.retry_delay = 30  # Start with 30 second retry delay
        self.max_retry_delay = 300  # Max 5 minute delay
        
    def connect(self) -> bool:
        """Attempt to connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host=self.config['host'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database']
            )
            self.retry_delay = 30  # Reset retry delay on successful connection
            return True
        except mysql.connector.Error as e:
            print(f"Database connection failed: {e}")
            self.connection = None
            return False
    
    def is_connected(self) -> bool:
        """Check if database connection is active"""
        if not self.connection:
            return False
        try:
            self.connection.ping(reconnect=False)
            return True
        except:
            return False
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[Any]:
        """Execute a database query with error handling"""
        if not self.is_connected():
            if not self.connect():
                return None
                
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                cursor.close()
                return result
            else:
                self.connection.commit()
                cursor.close()
                return True
                
        except mysql.connector.Error as e:
            print(f"Query execution failed: {e}")
            return None
    
    def get_current_counts(self, head_name: str) -> Dict[str, int]:
        """Get current confirmed and unconfirmed counts from database"""
        # Get confirmed count from heading_data
        confirmed_query = """
            SELECT reqCount, lastCountUpdate 
            FROM heading_data hea
            LEFT JOIN mfgreq_data mfg ON hea.reqID = mfg.reqLot
            WHERE headName = %s
        """
        confirmed_result = self.execute_query(confirmed_query, (head_name,))
        
        if not confirmed_result:
            return {"confirmed": 0, "unconfirmed": 0}
            
        confirmed_count = confirmed_result[0][0] or 0
        last_update = confirmed_result[0][1]
        
        # Get unconfirmed count from heading_rates since last update
        unconfirmed_query = """
            SELECT SUM(studCount) as smartCount 
            FROM heading_rates 
            WHERE headName = %s AND updateFullDate >= %s
        """
        unconfirmed_result = self.execute_query(unconfirmed_query, (head_name, last_update))
        
        unconfirmed_count = 0
        if unconfirmed_result and unconfirmed_result[0][0]:
            unconfirmed_count = unconfirmed_result[0][0]
            
        return {
            "confirmed": confirmed_count,
            "unconfirmed": unconfirmed_count
        }
    
    def upload_count_data(self, head_name: str, count: int) -> bool:
        """Upload count data to heading_rates table"""
        now = datetime.datetime.now()
        query = """
            INSERT INTO heading_rates 
            (headName, studCount, updateFullDate, updateDate, updateHour, updateMinute) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (head_name, count, now, now.strftime("%x"), now.hour, now.minute)
        
        result = self.execute_query(query, params)
        return result is not None
    
    def confirm_counts(self, head_name: str, new_count: int, user: str = "PI_SENSOR") -> bool:
        """Execute full confirmation workflow - move unconfirmed to confirmed"""
        now = datetime.datetime.now()
        
        # Update the confirmed count and timestamp in heading_data
        update_query = """
            UPDATE heading_data hea
            JOIN mfgreq_data mfg ON hea.reqID = mfg.reqLot
            SET mfg.reqCount = %s, hea.lastCountUpdate = %s
            WHERE hea.headName = %s
        """
        
        result = self.execute_query(update_query, (new_count, now, head_name))
        
        # Also update header status based on activity
        status_query = """
            UPDATE heading_data 
            SET headStatus = %s 
            WHERE headName = %s
        """
        status = 'ACTIVE' if new_count > 0 else 'INACTIVE'
        self.execute_query(status_query, (status, head_name))
        
        return result is not None

class OfflineDataManager:
    """Manages local SQLite database for offline data storage"""
    
    def __init__(self, db_path: str = "/home/pi/sensor_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the local SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                count INTEGER NOT NULL,
                uploaded BOOLEAN DEFAULT FALSE,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_count_record(self, count: int) -> bool:
        """Add a count record to local storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO offline_counts (timestamp, count)
                VALUES (?, ?)
            """, (timestamp, count))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Failed to add count record: {e}")
            return False
    
    def get_pending_records(self) -> List[CountRecord]:
        """Get all unuploaded count records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, timestamp, count, retry_count
                FROM offline_counts 
                WHERE uploaded = FALSE
                ORDER BY timestamp ASC
            """)
            
            records = []
            for row in cursor.fetchall():
                record = CountRecord(
                    timestamp=datetime.datetime.fromisoformat(row[1]),
                    count=row[2],
                    uploaded=False,
                    retry_count=row[3]
                )
                record.db_id = row[0]  # Store DB ID for updates
                records.append(record)
            
            conn.close()
            return records
            
        except Exception as e:
            print(f"Failed to get pending records: {e}")
            return []
    
    def mark_uploaded(self, record_ids: List[int]):
        """Mark records as successfully uploaded"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            placeholders = ','.join('?' * len(record_ids))
            cursor.execute(f"""
                UPDATE offline_counts 
                SET uploaded = TRUE 
                WHERE id IN ({placeholders})
            """, record_ids)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Failed to mark records as uploaded: {e}")
    
    def increment_retry_count(self, record_id: int):
        """Increment retry count for a failed upload"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE offline_counts 
                SET retry_count = retry_count + 1 
                WHERE id = ?
            """, (record_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Failed to increment retry count: {e}")
    
    def get_total_pending_count(self) -> int:
        """Get sum of all pending upload counts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT SUM(count) FROM offline_counts WHERE uploaded = FALSE
            """)
            
            result = cursor.fetchone()[0]
            conn.close()
            
            return result or 0
            
        except Exception as e:
            print(f"Failed to get total pending count: {e}")
            return 0

class DisplayManager:
    """Manages OLED display and screen navigation"""
    
    def __init__(self):
        # Initialize OLED display (commented out until hardware is available)
        # self.device = ssd1306(spi(device=0, port=0))
        # self.font = ImageFont.load_default()
        pass
    
    def _get_device_ip(self):
        """Get the device's IP address"""
        import socket
        try:
            # Create a socket connection to determine the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Connect to a remote address (doesn't actually send data)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
            return ip_address
        except Exception:
            try:
                # Fallback method using hostname
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
                return ip_address
            except Exception:
                return "Unknown"
    
    def render_screen(self, screen: DisplayScreen, state: SystemState):
        """Render the specified screen with current state"""
        if screen == DisplayScreen.LIVE_COUNT:
            self._render_live_count_screen(state)
        elif screen == DisplayScreen.UNCONFIRMED_TOTAL:
            self._render_unconfirmed_total_screen(state)
        elif screen == DisplayScreen.CONNECTION_STATUS:
            self._render_connection_status_screen(state)
    
    def _render_live_count_screen(self, state: SystemState):
        """Render live count screen"""
        # For now, just print to console (will be OLED display)
        status_text = "PAUSED" if state.counting_paused else "COUNTING"
        print(f"\n=== LIVE COUNT ===")
        print(f"Count: {state.live_count}")
        print(f"Status: {status_text}")
        print(f"Last Detection: {state.last_detection_time or 'None'}")
        
        # TODO: Implement actual OLED rendering
        # with canvas(self.device) as draw:
        #     draw.text((0, 0), "LIVE COUNT", font=self.font, fill="white")
        #     draw.text((0, 15), f"Count: {state.live_count}", font=self.font, fill="white")
        #     draw.text((0, 30), f"Status: {status_text}", font=self.font, fill="white")
    
    def _render_unconfirmed_total_screen(self, state: SystemState):
        """Render unconfirmed total screen"""
        print(f"\n=== UNCONFIRMED TOTAL ===")
        print(f"Confirmed: {state.last_confirmed_count}")
        print(f"Unconfirmed DB: {state.unconfirmed_count}")
        print(f"Live: {state.live_count}")
        print(f"Pending: {state.pending_upload_count}")
        print(f"TOTAL: {state.total_unconfirmed_count}")
    
    def _render_connection_status_screen(self, state: SystemState):
        """Render connection status screen"""
        status_symbols = {
            ConnectionStatus.CONNECTED: "✓ ONLINE",
            ConnectionStatus.DISCONNECTED: "✗ OFFLINE", 
            ConnectionStatus.RECONNECTING: "↻ CONNECTING",
            ConnectionStatus.ERROR: "⚠ ERROR"
        }
        
        # Get device IP address
        device_ip = self._get_device_ip()
        
        print(f"\n=== CONNECTION STATUS ===")
        print(f"IP Address: {device_ip}")
        print(f"Status: {status_symbols.get(state.connection_status, 'UNKNOWN')}")
        print(f"Last Sync: {state.last_sync_time or 'Never'}")
        print(f"Pending Upload: {state.pending_upload_count} counts")
        
        # Show connection indicator
        if state.connection_status == ConnectionStatus.CONNECTED:
            print("Database: READY")
        else:
            print("Database: NOT AVAILABLE")

class ButtonHandler:
    """Handles button and joystick input from Waveshare HAT"""
    
    def __init__(self, sensor_system):
        self.sensor_system = sensor_system
        self.setup_gpio()
    
    def setup_gpio(self):
        """Setup GPIO pins for buttons and joystick"""
        # Waveshare 1.3" OLED HAT pin mapping (example - verify with actual HAT)
        # These pins need to be confirmed with the actual hardware documentation
        self.BUTTON1_PIN = 21  # Key1
        self.BUTTON2_PIN = 20  # Key2  
        self.BUTTON3_PIN = 16  # Key3
        
        self.JOYSTICK_UP_PIN = 6    # Joystick Up
        self.JOYSTICK_DOWN_PIN = 19  # Joystick Down
        self.JOYSTICK_LEFT_PIN = 5   # Joystick Left
        self.JOYSTICK_RIGHT_PIN = 26 # Joystick Right
        self.JOYSTICK_CENTER_PIN = 13 # Joystick Center Press
        
        # Setup button pins
        for pin in [self.BUTTON1_PIN, self.BUTTON2_PIN, self.BUTTON3_PIN,
                   self.JOYSTICK_UP_PIN, self.JOYSTICK_DOWN_PIN, 
                   self.JOYSTICK_LEFT_PIN, self.JOYSTICK_RIGHT_PIN, 
                   self.JOYSTICK_CENTER_PIN]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pin, GPIO.FALLING, callback=self._button_callback, bouncetime=200)
    
    def _button_callback(self, channel):
        """Handle button press events"""
        if channel == self.BUTTON1_PIN:
            self.sensor_system.toggle_pause()
        elif channel == self.BUTTON2_PIN:
            self.sensor_system.reset_count()
        elif channel == self.BUTTON3_PIN:
            self.sensor_system.confirm_count()
        elif channel == self.JOYSTICK_LEFT_PIN:
            self.sensor_system.previous_screen()
        elif channel == self.JOYSTICK_RIGHT_PIN:
            self.sensor_system.next_screen()
        # Add more button mappings as needed

class SensorSystem:
    """Main sensor system class - coordinates all components"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state = SystemState()
        
        # Initialize components
        self.db_manager = DatabaseManager(config['database'])
        self.offline_manager = OfflineDataManager()
        self.display_manager = DisplayManager()
        self.button_handler = ButtonHandler(self)
        
        # Sensor setup
        self.sensor_pin = config.get('sensor_pin', 17)
        self.old_state = 2  # Initialize to impossible state to catch first reading
        self.setup_sensor()
        
        # Threading for background tasks
        self.running = True
        self.sync_thread = threading.Thread(target=self._background_sync_loop)
        self.display_thread = threading.Thread(target=self._display_update_loop)
        
        print("Sensor System 2.0 initialized")
    
    def setup_sensor(self):
        """Initialize the inductive sensor GPIO"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        print(f"Sensor initialized on pin {self.sensor_pin}")
    
    def detect_metal(self):
        """Check for metal detection and update counts"""
        if self.state.counting_paused:
            return
            
        new_state = GPIO.input(self.sensor_pin)
        
        if new_state != self.old_state:
            if new_state == 1:  # Metal detected (rising edge)
                self.state.live_count += 1
                self.state.last_detection_time = datetime.datetime.now()
                print(f"Metal detected! Live count: {self.state.live_count}")
            self.old_state = new_state
    
    def toggle_pause(self):
        """Toggle counting pause state (Button 1)"""
        self.state.counting_paused = not self.state.counting_paused
        status = "PAUSED" if self.state.counting_paused else "RESUMED"
        print(f"Counting {status}")
    
    def reset_count(self):
        """Reset live count (Button 2)"""
        self.state.live_count = 0
        print("Live count reset to 0")
    
    def confirm_count(self):
        """Confirm current counts - full workflow (Button 3)"""
        if self.state.live_count == 0:
            print("No live count to confirm")
            return
            
        print(f"Confirming {self.state.live_count} counts...")
        
        # Try to execute full confirmation workflow
        if self.state.connection_status == ConnectionStatus.CONNECTED:
            # Calculate new confirmed total
            new_total = self.state.total_unconfirmed_count
            
            # Upload current live count first
            if self.db_manager.upload_count_data(self.config['head_name'], self.state.live_count):
                # Execute confirmation workflow
                if self.db_manager.confirm_counts(self.config['head_name'], new_total):
                    print(f"Successfully confirmed {new_total} total counts")
                    # Reset local state
                    self.state.last_confirmed_count = new_total
                    self.state.unconfirmed_count = 0
                    self.state.live_count = 0
                    self.state.pending_upload_count = 0
                    # Clear any pending offline records
                    pending_records = self.offline_manager.get_pending_records()
                    if pending_records:
                        record_ids = [getattr(r, 'db_id', None) for r in pending_records if hasattr(r, 'db_id')]
                        self.offline_manager.mark_uploaded(record_ids)
                else:
                    print("Failed to confirm counts in database")
            else:
                print("Failed to upload live count")
        else:
            # Store for later confirmation when connection restored
            self.offline_manager.add_count_record(self.state.live_count)
            self.state.pending_upload_count = self.offline_manager.get_total_pending_count()
            self.state.live_count = 0
            print(f"Stored count offline. Pending: {self.state.pending_upload_count}")
    
    def next_screen(self):
        """Navigate to next display screen (Joystick Right)"""
        screens = list(DisplayScreen)
        current_index = screens.index(self.state.current_screen)
        next_index = (current_index + 1) % len(screens)
        self.state.current_screen = screens[next_index]
        print(f"Switched to screen: {self.state.current_screen.value}")
    
    def previous_screen(self):
        """Navigate to previous display screen (Joystick Left)"""
        screens = list(DisplayScreen)
        current_index = screens.index(self.state.current_screen)
        prev_index = (current_index - 1) % len(screens)
        self.state.current_screen = screens[prev_index]
        print(f"Switched to screen: {self.state.current_screen.value}")
    
    def _background_sync_loop(self):
        """Background thread for database synchronization"""
        while self.running:
            try:
                # Check connection status
                if self.db_manager.is_connected():
                    if self.state.connection_status != ConnectionStatus.CONNECTED:
                        self.state.connection_status = ConnectionStatus.CONNECTED
                        print("Database connection restored")
                        
                    # Sync current counts from database
                    counts = self.db_manager.get_current_counts(self.config['head_name'])
                    self.state.last_confirmed_count = counts['confirmed']
                    self.state.unconfirmed_count = counts['unconfirmed']
                    
                    # Try to upload pending offline data
                    pending_records = self.offline_manager.get_pending_records()
                    if pending_records:
                        uploaded_ids = []
                        for record in pending_records:
                            if self.db_manager.upload_count_data(self.config['head_name'], record.count):
                                uploaded_ids.append(getattr(record, 'db_id'))
                            else:
                                self.offline_manager.increment_retry_count(getattr(record, 'db_id'))
                        
                        if uploaded_ids:
                            self.offline_manager.mark_uploaded(uploaded_ids)
                            print(f"Uploaded {len(uploaded_ids)} pending records")
                    
                    # Update pending count
                    self.state.pending_upload_count = self.offline_manager.get_total_pending_count()
                    self.state.last_sync_time = datetime.datetime.now()
                    
                else:
                    # Try to reconnect
                    if self.state.connection_status == ConnectionStatus.CONNECTED:
                        self.state.connection_status = ConnectionStatus.RECONNECTING
                        print("Database connection lost, attempting to reconnect...")
                        
                    if not self.db_manager.connect():
                        self.state.connection_status = ConnectionStatus.DISCONNECTED
                    
            except Exception as e:
                print(f"Error in sync loop: {e}")
                self.state.connection_status = ConnectionStatus.ERROR
                
            time.sleep(30)  # Sync every 30 seconds
    
    def _display_update_loop(self):
        """Background thread for display updates"""
        while self.running:
            try:
                self.display_manager.render_screen(self.state.current_screen, self.state)
                time.sleep(1)  # Update display every second
            except Exception as e:
                print(f"Error in display loop: {e}")
                time.sleep(5)
    
    def start(self):
        """Start the sensor system"""
        print("Starting Sensor System 2.0...")
        
        # Start background threads
        self.sync_thread.start()
        self.display_thread.start()
        
        # Initial connection attempt
        if self.db_manager.connect():
            self.state.connection_status = ConnectionStatus.CONNECTED
            print("Connected to database")
        else:
            self.state.connection_status = ConnectionStatus.DISCONNECTED
            print("Starting in offline mode")
        
        # Main detection loop
        try:
            while self.running:
                self.detect_metal()
                time.sleep(0.1)  # Check sensor 10 times per second
                
        except KeyboardInterrupt:
            print("Shutting down...")
            self.stop()
    
    def stop(self):
        """Stop the sensor system"""
        self.running = False
        
        if self.sync_thread.is_alive():
            self.sync_thread.join()
        if self.display_thread.is_alive():
            self.display_thread.join()
            
        GPIO.cleanup()
        print("Sensor System stopped")

# Configuration and main execution
if __name__ == '__main__':
    config = {
        'head_name': 'NATIONAL_1',  # Configure for your specific header
        'sensor_pin': 17,
        'database': {
            'host': '192.168.1.54',  # Use consistent host
            'user': 'webapp',
            'password': 'STUDS2650',
            'database': 'iwt_db'
        }
    }
    
    # Initialize and start the system
    sensor_system = SensorSystem(config)
    
    try:
        sensor_system.start()
    except Exception as e:
        print(f"System error: {e}")
        sensor_system.stop()