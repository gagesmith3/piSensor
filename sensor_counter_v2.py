#!/usr/bin/env python3
"""
CONNECT - Sensor Counter v2.0
Clean production interface for Sacma SP-21 heading machine
No animations - pure functionality
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
        """Simple loading screen"""
        with canvas(self.device) as draw:
            draw.text((35, 15), "CONNECT", font=self.font, fill="white")
            draw.text((15, 30), "Sensor Counter", font=self.font, fill="white")
            draw.text((45, 45), "v2.0", font=self.font, fill="white")
        time.sleep(2)
    
    def draw_status_bar(self, draw):
        """Status bar at top of screen"""
        # Top bar border (12 pixels tall)
        draw.rectangle((0, 0, 127, 12), outline="white", fill="black")
        
        # Connection status icon (left)
        if self.connection_status == "ONLINE":
            # WiFi icon
            draw.arc((2, 3, 10, 9), 0, 180, fill="white")
            draw.arc((4, 4, 8, 8), 0, 180, fill="white")
            draw.point((6, 7), fill="white")
        elif self.connection_status == "CONNECTING":
            # Connecting
            draw.text((2, 2), "...", font=self.font, fill="white")
        else:
            # Offline X
            draw.line((2, 3, 8, 9), fill="white")
            draw.line((8, 3, 2, 9), fill="white")
        
        # Counting status (middle)
        status_text = "COUNTING" if self.counting_active else "PAUSED"
        draw.text((40, 2), status_text, font=self.font, fill="white")
        
        # Clock (right)
        time_str = datetime.now().strftime('%H:%M')
        draw.text((95, 2), time_str, font=self.font, fill="white")
        
        # Bottom border line
        draw.line((0, 12, 127, 12), fill="white")
    
    def draw_main_screen(self):
        """Main screen - live counter with unconfirmed total"""
        with canvas(self.device) as draw:
            # Status bar
            self.draw_status_bar(draw)
            
            # Live count - large text in center
            count_str = str(self.live_count)
            
            # Calculate centered position for 3x scaled text
            char_width = 8
            scale = 3
            start_x = 64 - (len(count_str) * char_width * scale // 2)
            start_y = 28
            
            # Draw large count
            for i, char in enumerate(count_str):
                x_pos = start_x + (i * char_width * scale)
                for dy in range(scale):
                    for dx in range(scale):
                        draw.text((x_pos + dx, start_y + dy), char, 
                                font=self.font, fill="white")
            
            # Unconfirmed total below
            draw.text((20, 55), f"Unconfirmed: {self.unconfirmed_total}", 
                     font=self.font, fill="white")
    
    def draw_settings_screen(self):
        """System settings screen"""
        with canvas(self.device) as draw:
            # Status bar
            self.draw_status_bar(draw)
            
            # Title
            draw.text((5, 15), "SYSTEM SETTINGS", font=self.font, fill="white")
            draw.line((0, 24, 127, 24), fill="white")
            
            # IP Address
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except:
                ip = "Not Connected"
            draw.text((0, 27), f"IP: {ip}", font=self.font, fill="white")
            
            # Database status
            db_status = "CONNECTED" if self.db_connected else "DISCONNECTED"
            draw.text((0, 37), f"DB: {db_status}", font=self.font, fill="white")
            
            # Header name
            draw.text((0, 47), f"Header: {self.header_name}", font=self.font, fill="white")
            
            # Sensor GPIO
            draw.text((0, 57), "Sensor: GPIO 17", font=self.font, fill="white")
    
    def draw_controls_screen(self):
        """Header controls screen"""
        with canvas(self.device) as draw:
            # Status bar
            self.draw_status_bar(draw)
            
            # Title
            draw.text((10, 15), "HEADER CONTROLS", font=self.font, fill="white")
            draw.line((0, 24, 127, 24), fill="white")
            
            # Control options
            draw.text((0, 28), "UP/DOWN: Adjust", font=self.font, fill="white")
            draw.text((0, 38), "KEY1: Toggle Count", font=self.font, fill="white")
            draw.text((0, 48), "KEY2: Confirm", font=self.font, fill="white")
            draw.text((0, 58), "KEY3: Reset", font=self.font, fill="white")
    
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
