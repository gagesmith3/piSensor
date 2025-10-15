#!/usr/bin/env python3
"""
CONNECT ERP - Header Counter Module v2.0

Part of the CONNECT ERP System for IWT Stud Welding
Deployed to 11 heading machines for real-time production tracking

Hardware: Raspberry Pi Zero W2 with Waveshare 1.3" OLED HAT
Purpose: Count studs produced by heading machines and sync data to CONNECT ERP
Features: 
- Real-time counter display with physical screen control
- Database synchronization with CONNECT ERP system
- Status monitoring and production tracking
- Manual counter adjustment via buttons

IWT Stud Welding - Production Counter
Version 2.0 - October 2025
"""

import time
import sys
from datetime import datetime

try:
    import RPi.GPIO as GPIO
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    from PIL import ImageFont
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("\nPlease install required packages:")
    print("  pip install luma.oled pillow RPi.GPIO spidev")
    sys.exit(1)

# GPIO pin definitions (BCM)
KEY1_PIN = 21
KEY2_PIN = 20
KEY3_PIN = 16
JOYSTICK_UP = 6
JOYSTICK_DOWN = 19
JOYSTICK_LEFT = 5
JOYSTICK_RIGHT = 26
JOYSTICK_PRESS = 13
SENSOR_PIN = 17

DC_PIN = 24
RST_PIN = 25

class SensorCounter:
    def __init__(self):
        print("Initializing CONNECT Sensor Counter v2.0...")
        
        # Setup GPIO
        self.setup_gpio()
        
        # Setup display
        self.setup_display()
        
        # Production variables
        self.live_count = 0
        self.unconfirmed_total = 0
        self.connection_status = "OFFLINE"  # ONLINE, OFFLINE, CONNECTING
        self.counting_active = False
        self.db_connected = False
        self.header_name = "H1-SP21"
        
        # Screen control
        self.current_screen = 0  # 0=main, 1=settings, 2=controls, 3=exit
        self.last_button = "None"
        
        # Button state tracking (for polling)
        self.button_states = {}
        self.pin_map = {
            KEY1_PIN: 'KEY1', KEY2_PIN: 'KEY2', KEY3_PIN: 'KEY3',
            JOYSTICK_UP: 'UP', JOYSTICK_DOWN: 'DOWN', 
            JOYSTICK_LEFT: 'LEFT', JOYSTICK_RIGHT: 'RIGHT', 
            JOYSTICK_PRESS: 'PRESS',
            SENSOR_PIN: 'SENSOR'
        }
        
        for pin in self.pin_map.keys():
            try:
                self.button_states[pin] = GPIO.input(pin)
            except:
                self.button_states[pin] = 1
        
        # Show load screen
        self.show_load_screen()
    
    def setup_gpio(self):
        """Initialize GPIO pins"""
        GPIO.setmode(GPIO.BCM)
        print("✓ GPIO mode set to BCM")
        
        # Button and sensor pins (all inputs with pull-up)
        pins = [KEY1_PIN, KEY2_PIN, KEY3_PIN, JOYSTICK_UP, JOYSTICK_DOWN,
                JOYSTICK_LEFT, JOYSTICK_RIGHT, JOYSTICK_PRESS, SENSOR_PIN]
        
        for pin in pins:
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                print(f"✓ GPIO {pin} configured")
            except Exception as e:
                print(f"✗ GPIO {pin} setup failed: {e}")
        
        print("✓ All GPIO pins configured (polling mode)")
    
    def setup_display(self):
        """Initialize OLED display"""
        print("Initializing display (SH1106, 4-wire SPI)...")
        try:
            serial = spi(device=0, port=0, bus_speed_hz=8000000, 
                        dc_pin=DC_PIN, rst_pin=RST_PIN)
            self.device = sh1106(serial, rotate=2)
            print(f"✓ Display initialized: {self.device.width}x{self.device.height}")
        except Exception as e:
            print(f"✗ Display init failed: {e}")
            sys.exit(1)
        
        try:
            self.font = ImageFont.load_default()
        except:
            self.font = None
    
    def show_load_screen(self):
        """Branded loading screen with animation"""
        # Frame 1: CONNECT ERP branding
        with canvas(self.device) as draw:
            # CONNECT title (centered)
            draw.text((35, 20), "CONNECT", font=self.font, fill="white")
            # Subtitle
            draw.text((15, 35), "ERP System v2.0", font=self.font, fill="white")
        time.sleep(1)
        
        # Frame 2: IWT Stud Welding branding
        with canvas(self.device) as draw:
            # Company name
            draw.text((10, 15), "IWT Stud Welding", font=self.font, fill="white")
            # Module type
            draw.text((15, 30), "Header Counter", font=self.font, fill="white")
            # Animated loading bar
            draw.rectangle((20, 45, 107, 50), outline="white", fill="black")
            draw.rectangle((22, 47, 52, 48), fill="white")  # 1/3 filled
        time.sleep(0.5)
        
        # Frame 3: Loading progress
        with canvas(self.device) as draw:
            draw.text((10, 15), "IWT Stud Welding", font=self.font, fill="white")
            draw.text((15, 30), "Header Counter", font=self.font, fill="white")
            draw.rectangle((20, 45, 107, 50), outline="white", fill="black")
            draw.rectangle((22, 47, 82, 48), fill="white")  # 2/3 filled
        time.sleep(0.5)
        
        # Frame 4: Ready
        with canvas(self.device) as draw:
            draw.text((10, 15), "IWT Stud Welding", font=self.font, fill="white")
            draw.text((15, 30), "Header Counter", font=self.font, fill="white")
            draw.rectangle((20, 45, 107, 50), outline="white", fill="black")
            draw.rectangle((22, 47, 105, 48), fill="white")  # Full
        time.sleep(0.3)
        
        # Frame 5: Header identification
        with canvas(self.device) as draw:
            # Header name (large)
            header_width = len(self.header_name) * 6
            start_x = 64 - (header_width // 2)
            # Draw header name slightly larger for emphasis
            for dy in range(2):
                for dx in range(2):
                    draw.text((start_x + dx, 20 + dy), self.header_name, 
                             font=self.font, fill="white")
            # Ready indicator
            draw.text((40, 40), "READY", font=self.font, fill="white")
        time.sleep(1)
    
    def draw_status_bar(self, draw):
        """Status bar at top of screen"""
        # Top bar border (12 pixels tall)
        draw.rectangle((0, 0, 127, 12), outline="white", fill="black")
        
        # LEFT: Connection status (checkmark or X)
        if self.connection_status == "ONLINE" or self.db_connected:
            # Checkmark
            draw.line((3, 6, 5, 8), fill="white", width=1)
            draw.line((5, 8, 9, 4), fill="white", width=1)
        else:
            # X symbol
            draw.line((3, 4, 8, 9), fill="white")
            draw.line((8, 4, 3, 9), fill="white")
        
        # CENTER: Progress bar with percentage
        # Calculate progress (for testing: 1-10 count = 10-100%)
        if self.live_count >= 10:
            progress_percent = 100
        elif self.live_count > 0:
            progress_percent = self.live_count * 10
        else:
            progress_percent = 0
        
        # Progress bar dimensions (moved left to make room for percentage)
        bar_x = 25
        bar_y = 4
        bar_width = 45
        bar_height = 5
        
        # Bar outline
        draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), 
                      outline="white", fill="black")
        
        # Filled portion
        if progress_percent > 0:
            fill_width = int((bar_width - 2) * (progress_percent / 100))
            if fill_width > 0:
                draw.rectangle((bar_x + 1, bar_y + 1, 
                              bar_x + 1 + fill_width, bar_y + bar_height - 1), 
                              fill="white")
        
        # Percentage text (right of progress bar)
        percent_text = f"{progress_percent}%"
        draw.text((bar_x + bar_width + 3, 3), percent_text, font=self.font, fill="white")
        
        # RIGHT: Header status (paused or running symbols)
        if self.counting_active:
            # Running symbol (triangle play button)
            draw.polygon([(115, 4), (115, 9), (121, 6.5)], fill="white", outline="white")
        else:
            # Paused symbol (two vertical bars)
            draw.rectangle((115, 4, 117, 9), fill="white")
            draw.rectangle((119, 4, 121, 9), fill="white")
        
        # Bottom border line
        draw.line((0, 12, 127, 12), fill="white")
    
    def draw_main_screen(self):
        """Main screen - live counter"""
        with canvas(self.device) as draw:
            # Status bar
            self.draw_status_bar(draw)
            
            # Live count - formatted with commas for readability
            # Format number with commas (e.g., 1,234,567)
            count_formatted = f"{self.live_count:,}"
            
            # Draw centered with normal font weight
            text_width = len(count_formatted) * 6  # Approximate width
            start_x = 64 - (text_width // 2)
            start_y = 32
            
            # Draw once - clean, thin font
            draw.text((start_x, start_y), count_formatted, 
                     font=self.font, fill="white")
    
    def draw_settings_screen(self):
        """System settings screen"""
        with canvas(self.device) as draw:
            # Title with CONNECT branding
            draw.text((2, 2), "CONNECT | SETTINGS", font=self.font, fill="white")
            draw.line((0, 11, 127, 11), fill="white")
            
            # Header identification (most important)
            draw.text((0, 15), f"Header: {self.header_name}", font=self.font, fill="white")
            
            # Database connection to CONNECT ERP
            db_status = "ONLINE" if self.db_connected else "OFFLINE"
            draw.text((0, 27), f"ERP Link: {db_status}", font=self.font, fill="white")
            
            # IP Address
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except:
                ip = "No Network"
            draw.text((0, 39), f"IP: {ip}", font=self.font, fill="white")
            
            # Sensor status
            draw.text((0, 51), "Sensor: GPIO 17", font=self.font, fill="white")
    
    def draw_controls_screen(self):
        """Header controls screen"""
        with canvas(self.device) as draw:
            # Title (no status bar)
            draw.text((10, 2), "HEADER CONTROLS", font=self.font, fill="white")
            draw.line((0, 11, 127, 11), fill="white")
            
            # Control options
            draw.text((0, 16), "UP/DOWN: Adjust", font=self.font, fill="white")
            draw.text((0, 28), "KEY1: Toggle Count", font=self.font, fill="white")
            draw.text((0, 40), "KEY2: Confirm", font=self.font, fill="white")
            draw.text((0, 52), "KEY3: Reset", font=self.font, fill="white")
    
    def draw_exit_screen(self):
        """Exit confirmation screen"""
        with canvas(self.device) as draw:
            draw.rectangle((10, 15, 118, 50), outline="white", fill="black")
            draw.text((25, 23), "Exit CONNECT?", font=self.font, fill="white")
            draw.text((15, 35), "PRESS: Confirm", font=self.font, fill="white")
            draw.text((15, 43), "LEFT: Cancel", font=self.font, fill="white")
    
    def poll_buttons(self):
        """Poll all buttons for state changes"""
        for pin, name in self.pin_map.items():
            try:
                current_state = GPIO.input(pin)
                previous_state = self.button_states.get(pin, 1)
                
                # Detect falling edge (button press)
                if previous_state == 1 and current_state == 0:
                    self.handle_button_press(name)
                
                self.button_states[pin] = current_state
            except:
                pass
    
    def handle_button_press(self, btn):
        """Handle button press events"""
        self.last_button = btn
        
        # Navigation (LEFT/RIGHT work on all screens except exit)
        if btn == 'LEFT':
            if self.current_screen == 3:  # Exit screen - cancel
                self.current_screen = 0
            else:
                self.current_screen = (self.current_screen - 1) % 3
        
        elif btn == 'RIGHT':
            if self.current_screen < 3:
                self.current_screen = (self.current_screen + 1) % 3
        
        # Sensor detection
        elif btn == 'SENSOR':
            if self.counting_active:
                self.live_count += 1
                self.unconfirmed_total += 1
                print(f"Part detected! Count: {self.live_count}")
        
        # Screen-specific controls
        if self.current_screen == 0:  # Main screen
            if btn == 'UP':
                # Manual increment (testing)
                self.live_count += 1
                self.unconfirmed_total += 1
            elif btn == 'DOWN':
                # Manual decrement (testing)
                self.live_count = max(0, self.live_count - 1)
                self.unconfirmed_total = max(0, self.unconfirmed_total - 1)
            elif btn == 'KEY1':
                # Toggle counting
                self.counting_active = not self.counting_active
                print(f"Counting: {'ON' if self.counting_active else 'OFF'}")
            elif btn == 'KEY2':
                # Confirm count (reset unconfirmed)
                self.unconfirmed_total = 0
                print(f"Count confirmed: {self.live_count}")
            elif btn == 'KEY3':
                # Reset counter
                self.live_count = 0
                self.unconfirmed_total = 0
                print("Counter reset")
        
        elif self.current_screen == 1:  # Settings screen
            if btn == 'KEY1':
                # Toggle connection (testing)
                statuses = ["OFFLINE", "CONNECTING", "ONLINE"]
                idx = statuses.index(self.connection_status)
                self.connection_status = statuses[(idx + 1) % 3]
                self.db_connected = (self.connection_status == "ONLINE")
        
        elif self.current_screen == 2:  # Controls screen
            pass  # Controls are display only for now
        
        elif self.current_screen == 3:  # Exit screen
            if btn == 'PRESS':
                # Confirm exit
                return True  # Signal to exit
        
        # Long press on PRESS to go to exit screen
        if btn == 'PRESS' and self.current_screen != 3:
            # Simple press goes to exit (we'll improve this later)
            pass
        
        return False  # Don't exit
    
    def update_display(self):
        """Update display based on current screen"""
        if self.current_screen == 0:
            self.draw_main_screen()
        elif self.current_screen == 1:
            self.draw_settings_screen()
        elif self.current_screen == 2:
            self.draw_controls_screen()
        elif self.current_screen == 3:
            self.draw_exit_screen()
    
    def run(self):
        """Main run loop"""
        print("\n" + "="*60)
        print("CONNECT - Sensor Counter v2.0 Running")
        print("="*60)
        print("\nControls:")
        print("  LEFT/RIGHT  - Navigate screens")
        print("  UP/DOWN     - Manual count adjust (testing)")
        print("  KEY1        - Toggle counting ON/OFF")
        print("  KEY2        - Confirm/update count")
        print("  KEY3        - Reset counter")
        print("  Ctrl+C      - Exit")
        print("="*60 + "\n")
        
        try:
            last_poll = time.time()
            last_display_update = time.time()
            
            while True:
                current_time = time.time()
                
                # Poll buttons at 50Hz
                if current_time - last_poll >= 0.02:
                    should_exit = self.poll_buttons()
                    if should_exit:
                        break
                    last_poll = current_time
                
                # Update display at 10Hz
                if current_time - last_display_update >= 0.1:
                    self.update_display()
                    last_display_update = current_time
                
                time.sleep(0.005)
        
        except KeyboardInterrupt:
            print("\nStopped by user")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean shutdown"""
        print("Shutting down...")
        
        # Show exit screen
        with canvas(self.device) as draw:
            draw.rectangle((10, 20, 118, 45), outline="white", fill="black")
            draw.text((35, 28), "CONNECT", font=self.font, fill="white")
            draw.text((25, 38), "Shutdown...", font=self.font, fill="white")
        time.sleep(1)
        
        # Clear display
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
        
        # Cleanup GPIO
        GPIO.cleanup()
        print("✓ Cleanup complete")

def main():
    print("\n" + "="*60)
    print("   ____ ___  _   _ _   _ _____ ____ _____ ")
    print("  / ___/ _ \\| \\ | | \\ | | ____/ ___|_   _|")
    print(" | |  | | | |  \\| |  \\| |  _|| |     | |  ")
    print(" | |__| |_| | |\\  | |\\  | |__| |___  | |  ")
    print("  \\____\\___/|_| \\_|_| \\_|_____\\____| |_|  ")
    print("")
    print("  Sensor Counter v2.0 - Production System")
    print("  Sacma SP-21 Heading Machine")
    print("="*60 + "\n")
    
    try:
        counter = SensorCounter()
        counter.run()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    main()
