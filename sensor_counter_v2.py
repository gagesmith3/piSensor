#!/usr/bin/env python3
"""
CONNECT - Stud Sensor Module v2.0

Part of the CONNECT System for IWT Stud Welding
Deployed to 11 heading machines for real-time production tracking

Hardware: Raspberry Pi Zero W2 with Waveshare 1.3" OLED HAT
Purpose: Count studs produced by heading machines and sync data to CONNECT
Features: 
- Real-time counter display with physical screen control
- Database synchronization with CONNECT system
- Status monitoring and production tracking
- Manual counter adjustment via buttons

IWT Stud Welding - Stud Sensor
Version 2.0 - October 2025
"""

import time
import sys
import math
from datetime import datetime

try:
    import RPi.GPIO as GPIO
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    from PIL import ImageFont, Image, ImageDraw
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

class WeldStudAnimation:
    """3D rotating weld stud wireframe animation for Stud Sensor branding"""
    
    def __init__(self, device, font):
        self.device = device
        self.font = font
    
    def create_weld_stud_vertices(self, segments=8):
        """Create 3D vertices for a weld stud shape"""
        vertices = []
        
        # Head (larger diameter disc at top)
        head_radius = 1.2
        head_height = 0.3
        
        # Top circle of head
        for i in range(segments):
            angle = (i / segments) * 2 * math.pi
            x = head_radius * math.cos(angle)
            z = head_radius * math.sin(angle)
            vertices.append((x, head_height, z))
        
        # Bottom circle of head
        for i in range(segments):
            angle = (i / segments) * 2 * math.pi
            x = head_radius * math.cos(angle)
            z = head_radius * math.sin(angle)
            vertices.append((x, 0, z))
        
        # Shaft (smaller diameter cylinder)
        shaft_radius = 0.7
        shaft_height = -2.0
        
        # Top circle of shaft
        for i in range(segments):
            angle = (i / segments) * 2 * math.pi
            x = shaft_radius * math.cos(angle)
            z = shaft_radius * math.sin(angle)
            vertices.append((x, 0, z))
        
        # Bottom circle of shaft
        for i in range(segments):
            angle = (i / segments) * 2 * math.pi
            x = shaft_radius * math.cos(angle)
            z = shaft_radius * math.sin(angle)
            vertices.append((x, shaft_height, z))
        
        # Weld point at bottom
        vertices.append((0, shaft_height - 0.3, 0))
        
        return vertices
    
    def rotate_3d(self, vertices, angle_x, angle_y):
        """Rotate 3D vertices around X and Y axes"""
        rotated = []
        
        cos_x = math.cos(angle_x)
        sin_x = math.sin(angle_x)
        cos_y = math.cos(angle_y)
        sin_y = math.sin(angle_y)
        
        for x, y, z in vertices:
            # Rotate around Y axis
            temp_x = x * cos_y - z * sin_y
            temp_z = x * sin_y + z * cos_y
            
            # Rotate around X axis
            temp_y = y * cos_x - temp_z * sin_x
            final_z = y * sin_x + temp_z * cos_x
            
            rotated.append((temp_x, temp_y, final_z))
        
        return rotated
    
    def project_to_2d(self, vertices, cx=35, cy=32, scale=15, distance=5):
        """Project 3D vertices to 2D screen coordinates"""
        projected = []
        
        for x, y, z in vertices:
            factor = distance / (distance + z)
            screen_x = int(cx + x * scale * factor)
            screen_y = int(cy - y * scale * factor)
            projected.append((screen_x, screen_y))
        
        return projected
    
    def draw_weld_stud(self, draw, angle_x, angle_y, segments=8):
        """Draw the weld stud wireframe"""
        vertices_3d = self.create_weld_stud_vertices(segments)
        rotated = self.rotate_3d(vertices_3d, angle_x, angle_y)
        vertices_2d = self.project_to_2d(rotated)
        
        # Draw head top circle
        for i in range(segments):
            p1 = vertices_2d[i]
            p2 = vertices_2d[(i + 1) % segments]
            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
        
        # Draw head bottom circle
        offset = segments
        for i in range(segments):
            p1 = vertices_2d[offset + i]
            p2 = vertices_2d[offset + (i + 1) % segments]
            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
        
        # Draw head vertical lines
        for i in range(segments):
            p1 = vertices_2d[i]
            p2 = vertices_2d[segments + i]
            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
        
        # Draw shaft top circle
        offset = segments * 2
        for i in range(segments):
            p1 = vertices_2d[offset + i]
            p2 = vertices_2d[offset + (i + 1) % segments]
            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
        
        # Draw shaft bottom circle
        offset = segments * 3
        for i in range(segments):
            p1 = vertices_2d[offset + i]
            p2 = vertices_2d[offset + (i + 1) % segments]
            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
        
        # Draw shaft vertical lines
        for i in range(segments):
            p1 = vertices_2d[segments * 2 + i]
            p2 = vertices_2d[segments * 3 + i]
            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
        
        # Draw lines from shaft bottom to weld point
        weld_point = vertices_2d[-1]
        for i in range(0, segments, 2):
            p1 = vertices_2d[segments * 3 + i]
            draw.line((p1[0], p1[1], weld_point[0], weld_point[1]), fill="white")
    
    def animate_rotating_stud(self, frames=60):
        """Rotating weld stud animation"""
        for frame in range(frames):
            with canvas(self.device) as draw:
                # Rotation angles
                angle_y = frame * 0.08
                angle_x = math.sin(frame * 0.05) * 0.3
                
                # Draw the weld stud
                self.draw_weld_stud(draw, angle_x, angle_y, segments=10)
                
                # Stud Sensor branding
                draw.text((75, 15), "STUD", font=self.font, fill="white")
                draw.text((72, 28), "SENSOR", font=self.font, fill="white")
                draw.text((80, 50), "v2.0", font=self.font, fill="white")
            
            time.sleep(0.04)

class SensorCounter:
    def __init__(self):
        print("Initializing CONNECT Stud Sensor v2.0...")
        
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
        
        # Load default small font for UI elements
        try:
            self.font = ImageFont.load_default()
        except:
            self.font = None
        
        # Try to load a larger TrueType font specifically for the counter display
        try:
            # Try common TrueType font locations on Raspberry Pi
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            ]
            
            self.counter_font = None
            for font_path in font_paths:
                try:
                    # Load at larger size for direct rendering (bigger = 36)
                    self.counter_font = ImageFont.truetype(font_path, 36)
                    print(f"✓ Loaded TrueType counter font: {font_path}")
                    break
                except:
                    continue
            
            if self.counter_font is None:
                print("⚠ TrueType fonts not found, will use default for counter")
                self.counter_font = self.font
        except:
            self.counter_font = self.font
    
    def show_load_screen(self):
        """Branded loading screen with Stud Sensor animation"""
        # Frame 1: CONNECT / IWT Branding with animated divider
        frames_1 = 75  # 3 seconds @ 0.04s per frame
        for frame in range(frames_1):
            progress = frame / frames_1
            with canvas(self.device) as draw:
                # CONNECT text (fade in early)
                if progress > 0.2:
                    draw.text((35, 18), "CONNECT", font=self.font, fill="white")
                
                # Animated divider line grows from center
                if progress > 0.4:
                    line_progress = min(1.0, (progress - 0.4) / 0.3)
                    center = 64
                    half_width = int(34 * line_progress)
                    draw.line((center - half_width, 30, center + half_width, 30), fill="white")
                
                # IWT Stud Welding text (appears after line)
                if progress > 0.6:
                    draw.text((10, 38), "IWT Stud Welding", font=self.font, fill="white")
            
            time.sleep(0.04)
        
        # Frame 2: STUD SENSOR with 3D Weld Stud Animation (3 seconds)
        weld_anim = WeldStudAnimation(self.device, self.font)
        weld_anim.animate_rotating_stud(frames=75)  # 75 frames @ 0.04s = 3 seconds
        
        # Frame 3: Header Identification (centered, blinking READY only)
        frames_3 = 75  # 3 seconds @ 0.04s per frame
        for frame in range(frames_3):
            with canvas(self.device) as draw:
                # Stud Sensor branding (centered)
                draw.text((25, 8), "STUD SENSOR", font=self.font, fill="white")
                
                # Divider line (centered)
                draw.line((20, 20, 108, 20), fill="white")
                
                # Header name (large, centered)
                header_width = len(self.header_name) * 6
                start_x = 64 - (header_width // 2)
                for dy in range(2):
                    for dx in range(2):
                        draw.text((start_x + dx, 28 + dy), self.header_name, 
                                 font=self.font, fill="white")
                
                # Ready status - blinks continuously
                if int(frame / 8) % 2 == 0:  # Blink effect
                    draw.text((40, 48), "READY", font=self.font, fill="white")
            
            time.sleep(0.04)
    
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
            
            # Use the larger TrueType font directly (much cleaner rendering)
            try:
                # Get text bounding box for proper centering
                bbox = draw.textbbox((0, 0), count_formatted, font=self.counter_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Center the text
                start_x = (128 - text_width) // 2
                start_y = 30  # Below status bar
                
                # Draw with TrueType font (clean, anti-aliased)
                draw.text((start_x, start_y), count_formatted, 
                         font=self.counter_font, fill="white")
            except:
                # Fallback to old method if TrueType fails
                text_width = len(count_formatted) * 6
                start_x = 64 - (text_width // 2)
                start_y = 32
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
            
            # Database connection to CONNECT
            db_status = "ONLINE" if self.db_connected else "OFFLINE"
            draw.text((0, 27), f"DB Link: {db_status}", font=self.font, fill="white")
            
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
        """Clean shutdown with animation"""
        print("Shutting down...")
        
        # Animated shutdown screen (1.5 seconds)
        frames = 37  # ~1.5 seconds @ 0.04s per frame
        for frame in range(frames):
            progress = frame / frames
            with canvas(self.device) as draw:
                # Border box
                draw.rectangle((10, 20, 118, 45), outline="white", fill="black")
                
                # Title
                draw.text((22, 28), "STUD SENSOR", font=self.font, fill="white")
                
                # Shutting Down with animated dots
                dots = "." * (int(frame / 8) % 4)
                text = f"Shutting Down{dots}"
                draw.text((15, 38), text, font=self.font, fill="white")
                
                # Progress bar at bottom of box
                if progress > 0.2:
                    bar_progress = (progress - 0.2) / 0.8
                    bar_width = int(96 * bar_progress)
                    draw.rectangle((16, 50, 112, 54), outline="white", fill="black")
                    if bar_width > 0:
                        draw.rectangle((17, 51, 17 + bar_width, 53), fill="white")
            
            time.sleep(0.04)
        
        # Clear display with fade effect
        for i in range(3):
            with canvas(self.device) as draw:
                if i % 2 == 0:
                    draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            time.sleep(0.1)
        
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
