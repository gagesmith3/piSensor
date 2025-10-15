#!/usr/bin/env python3
"""
CONNECT - Custom 3D Weld Stud Animation
Rotating wireframe weld stud for factory branding
"""

import time
import sys
from datetime import datetime
import math

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

DC_PIN = 24
RST_PIN = 25

class WeldStudAnimation:
    """3D rotating weld stud wireframe animation"""
    
    def __init__(self, device, font):
        self.device = device
        self.font = font
    
    def create_weld_stud_vertices(self, segments=8):
        """
        Create 3D vertices for a weld stud
        Weld stud shape: flat head on top, cylindrical shaft below
        """
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
        
        # Bottom circle of head (where it meets shaft)
        for i in range(segments):
            angle = (i / segments) * 2 * math.pi
            x = head_radius * math.cos(angle)
            z = head_radius * math.sin(angle)
            vertices.append((x, 0, z))
        
        # Shaft (smaller diameter cylinder)
        shaft_radius = 0.7
        shaft_height = -2.0
        
        # Top circle of shaft (same as bottom of head)
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
        
        # Weld point at bottom (small tip)
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
        """Project 3D vertices to 2D screen coordinates with perspective"""
        projected = []
        
        for x, y, z in vertices:
            # Perspective projection
            factor = distance / (distance + z)
            screen_x = int(cx + x * scale * factor)
            screen_y = int(cy - y * scale * factor)
            projected.append((screen_x, screen_y))
        
        return projected
    
    def draw_weld_stud(self, draw, angle_x, angle_y, segments=8):
        """Draw the weld stud wireframe"""
        # Create and transform vertices
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
        for i in range(0, segments, 2):  # Only draw every other line to avoid clutter
            p1 = vertices_2d[segments * 3 + i]
            draw.line((p1[0], p1[1], weld_point[0], weld_point[1]), fill="white")
    
    def rotating_weld_stud_animation(self):
        """Main rotating weld stud animation"""
        print("  - Rotating weld stud animation")
        
        for frame in range(120):
            with canvas(self.device) as draw:
                # Rotation angles
                angle_y = frame * 0.05  # Rotate around vertical axis
                angle_x = math.sin(frame * 0.03) * 0.3  # Slight wobble
                
                # Draw the weld stud
                self.draw_weld_stud(draw, angle_x, angle_y, segments=12)
                
                # Add CONNECT branding
                draw.text((75, 8), "CONNECT", font=self.font, fill="white")
                draw.text((75, 22), "Weld Stud", font=self.font, fill="white")
                draw.text((75, 36), "Sensor", font=self.font, fill="white")
                draw.text((80, 50), "v2.0", font=self.font, fill="white")
            
            time.sleep(0.04)
    
    def weld_stud_assembly_animation(self):
        """Show weld stud being 'assembled' piece by piece"""
        print("  - Weld stud assembly animation")
        
        segments = 12
        
        # Build up the stud from bottom to top
        for build_progress in range(60):
            progress = build_progress / 59.0
            
            with canvas(self.device) as draw:
                angle_y = build_progress * 0.08
                angle_x = 0.2
                
                vertices_3d = self.create_weld_stud_vertices(segments)
                rotated = self.rotate_3d(vertices_3d, angle_x, angle_y)
                vertices_2d = self.project_to_2d(rotated)
                
                # Only draw portions based on progress
                # Progress 0-0.25: weld point
                if progress > 0:
                    weld_point = vertices_2d[-1]
                    draw.ellipse((weld_point[0]-2, weld_point[1]-2, 
                                weld_point[0]+2, weld_point[1]+2), fill="white")
                
                # Progress 0.25-0.5: shaft
                if progress > 0.25:
                    shaft_progress = (progress - 0.25) / 0.25
                    
                    # Draw shaft circles and lines
                    offset = segments * 3
                    for i in range(segments):
                        if i / segments < shaft_progress:
                            p1 = vertices_2d[offset + i]
                            p2 = vertices_2d[offset + (i + 1) % segments]
                            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
                    
                    # Shaft vertical lines
                    for i in range(segments):
                        if i / segments < shaft_progress:
                            p1 = vertices_2d[segments * 2 + i]
                            p2 = vertices_2d[segments * 3 + i]
                            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
                
                # Progress 0.5-0.75: shaft to weld point connection
                if progress > 0.5:
                    weld_point = vertices_2d[-1]
                    for i in range(0, segments, 2):
                        p1 = vertices_2d[segments * 3 + i]
                        draw.line((p1[0], p1[1], weld_point[0], weld_point[1]), fill="white")
                
                # Progress 0.75-1.0: head
                if progress > 0.75:
                    head_progress = (progress - 0.75) / 0.25
                    
                    # Head circles
                    for i in range(segments):
                        if i / segments < head_progress:
                            p1 = vertices_2d[i]
                            p2 = vertices_2d[(i + 1) % segments]
                            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
                    
                    # Head vertical lines
                    for i in range(segments):
                        if i / segments < head_progress:
                            p1 = vertices_2d[i]
                            p2 = vertices_2d[segments + i]
                            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="white")
                
                # Text appears at end
                if progress > 0.9:
                    draw.text((75, 12), "CONNECT", font=self.font, fill="white")
                    draw.text((75, 26), "Weld Stud", font=self.font, fill="white")
            
            time.sleep(0.05)
        
        time.sleep(0.5)
    
    def run_weld_stud_boot(self):
        """Run complete weld stud boot sequence"""
        print("Running weld stud boot animation...")
        
        # 1. Assembly animation
        self.weld_stud_assembly_animation()
        
        # 2. Rotating display
        self.rotating_weld_stud_animation()
        
        # 3. Final splash
        with canvas(self.device) as draw:
            draw.text((20, 5), "CONNECT", font=self.font, fill="white")
            draw.line((20, 20, 108, 20), fill="white", width=2)
            draw.text((10, 28), "Weld Stud Sensor", font=self.font, fill="white")
            draw.text((20, 42), "System Ready", font=self.font, fill="white")
            draw.text((48, 54), "v2.0", font=self.font, fill="white")
        
        time.sleep(1.5)
        
        print("✓ Weld stud boot complete!")

class DisplayTest:
    def __init__(self):
        print("Setting up GPIO (polling mode)...")
        self.setup_buttons()
        
        print("Initializing display (SH1106, 4-wire SPI)...")
        try:
            serial = spi(device=0, port=0, bus_speed_hz=8000000, dc_pin=DC_PIN, rst_pin=RST_PIN)
            self.device = sh1106(serial, rotate=2)
            print(f"✓ Display initialized: {self.device.width}x{self.device.height}")
        except Exception as e:
            print(f"✗ Display init failed: {e}")
            sys.exit(1)
        
        try:
            self.font = ImageFont.load_default()
        except:
            self.font = None
        
        # Run weld stud boot animation
        boot_anim = WeldStudAnimation(self.device, self.font)
        boot_anim.run_weld_stud_boot()
        
        self.button_presses = {k: 0 for k in ['KEY1','KEY2','KEY3','UP','DOWN','LEFT','RIGHT','PRESS']}
        self.last_button = "None"
        self.current_screen = 0
        self.test_counter = 0
        
        self.button_states = {}
        self.pin_map = {
            KEY1_PIN: 'KEY1', KEY2_PIN: 'KEY2', KEY3_PIN: 'KEY3',
            JOYSTICK_UP: 'UP', JOYSTICK_DOWN: 'DOWN', JOYSTICK_LEFT: 'LEFT',
            JOYSTICK_RIGHT: 'RIGHT', JOYSTICK_PRESS: 'PRESS'
        }
        
        for pin in self.pin_map.keys():
            try:
                self.button_states[pin] = GPIO.input(pin)
            except:
                self.button_states[pin] = 1
    
    def setup_buttons(self):
        GPIO.setmode(GPIO.BCM)
        print("✓ GPIO mode set to BCM")
        
        pins = [KEY1_PIN, KEY2_PIN, KEY3_PIN, JOYSTICK_UP, JOYSTICK_DOWN, 
                JOYSTICK_LEFT, JOYSTICK_RIGHT, JOYSTICK_PRESS]
        
        for pin in pins:
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                print(f"✓ GPIO {pin} configured")
            except Exception as e:
                print(f"✗ GPIO {pin} setup failed: {e}")
        
        print("✓ All buttons configured for POLLING")
    
    def poll_buttons(self):
        for pin, name in self.pin_map.items():
            try:
                current_state = GPIO.input(pin)
                previous_state = self.button_states.get(pin, 1)
                if previous_state == 1 and current_state == 0:
                    self.handle_button_press(name)
                self.button_states[pin] = current_state
            except:
                pass
    
    def handle_button_press(self, btn):
        self.button_presses[btn] += 1
        self.last_button = btn
        
        if btn == 'LEFT':
            self.current_screen = (self.current_screen - 1) % 4
        elif btn == 'RIGHT':
            self.current_screen = (self.current_screen + 1) % 4
        elif btn == 'UP':
            self.test_counter += 1
        elif btn == 'DOWN':
            self.test_counter = max(0, self.test_counter - 1)
        elif btn == 'PRESS':
            self.test_counter = 0
        
        print(f"Button: {btn} (Total: {self.button_presses[btn]})")
    
    def clear_display(self):
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
    
    def draw_screen_0(self):
        with canvas(self.device) as draw:
            draw.text((20, 5), "CONNECT", font=self.font, fill="white")
            draw.line((20, 20, 108, 20), fill="white", width=1)
            draw.text((5, 28), "Weld Stud Sensor", font=self.font, fill="white")
            draw.text((0, 45), "Use <- -> navigate", font=self.font, fill="white")
    
    def draw_screen_1(self):
        with canvas(self.device) as draw:
            draw.text((0, 0), "=== SYSTEM INFO ===", font=self.font, fill="white")
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except:
                ip = "N/A"
            draw.text((0, 15), f"IP: {ip}", font=self.font, fill="white")
            draw.text((0, 28), f"Time: {datetime.now().strftime('%H:%M:%S')}", font=self.font, fill="white")
            draw.text((0, 41), f"Counter: {self.test_counter}", font=self.font, fill="white")
            draw.text((0, 54), f"Screen: {self.current_screen + 1}/4", font=self.font, fill="white")
    
    def draw_screen_2(self):
        with canvas(self.device) as draw:
            draw.text((0, 0), "=== BUTTON TEST ===", font=self.font, fill="white")
            draw.text((0, 12), f"Last: {self.last_button}", font=self.font, fill="white")
            y = 25
            for btn in ['KEY1', 'KEY2', 'KEY3']:
                count = self.button_presses[btn]
                draw.text((0, y), f"{btn}: {count}", font=self.font, fill="white")
                y += 12
    
    def draw_screen_3(self):
        with canvas(self.device) as draw:
            draw.text((0, 0), "== JOYSTICK TEST ==", font=self.font, fill="white")
            y = 12
            for btn in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'PRESS']:
                count = self.button_presses[btn]
                draw.text((0, y), f"{btn}: {count}", font=self.font, fill="white")
                y += 10
    
    def run_test(self):
        print("\n" + "="*60)
        print("CONNECT - Weld Stud Sensor System")
        print("="*60)
        print("\nControls: LEFT/RIGHT navigate, UP/DOWN counter, PRESS reset")
        print("          KEY1/2/3 test buttons, Ctrl+C exit")
        print("="*60 + "\n")
        
        try:
            last_poll = time.time()
            last_display_update = time.time()
            
            while True:
                current_time = time.time()
                
                if current_time - last_poll >= 0.02:
                    self.poll_buttons()
                    last_poll = current_time
                
                if current_time - last_display_update >= 0.1:
                    if self.current_screen == 0:
                        self.draw_screen_0()
                    elif self.current_screen == 1:
                        self.draw_screen_1()
                    elif self.current_screen == 2:
                        self.draw_screen_2()
                    elif self.current_screen == 3:
                        self.draw_screen_3()
                    
                    last_display_update = current_time
                
                time.sleep(0.005)
                
        except KeyboardInterrupt:
            print("\nTest stopped by user")
            self.cleanup()
    
    def cleanup(self):
        print("Cleaning up...")
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            draw.text((30, 25), "CONNECT", font=self.font, fill="white")
            draw.text((20, 40), "Shutdown...", font=self.font, fill="white")
        time.sleep(1)
        self.clear_display()
        GPIO.cleanup()
        print("✓ Cleanup complete")

def main():
    print("\n" + "="*60)
    print("   ____  ___   _   ___   ____________")
    print("  / ___\\/ _ \\ / | / / | / / ____/ ___/___  __")
    print(" / /   / / / /  |/ /  |/ / __/ / /     / / ")
    print("/ /___/ /_/ / /|  / /|  / /___/ /___  / / ")
    print("\\____/\\____/_/ |_/_/ |_/_____/\\____/ /_/")
    print("")
    print("  WELD STUD SENSOR - Factory Edition v2.0")
    print("  Custom 3D Wireframe Animation")
    print("="*60 + "\n")
    
    try:
        test = DisplayTest()
        test.run_test()
    except KeyboardInterrupt:
        print("\nTest interrupted")
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
