#!/usr/bin/env python3
"""
CONNECT - 80s Retro Boot Animation
Tron-style vectors, neon grids, scanlines, and retro effects
"""

import time
import sys
from datetime import datetime
import math
import random

try:
    import RPi.GPIO as GPIO
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    from PIL import ImageFont, ImageDraw, Image
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

class Retro80sAnimation:
    """80s-style retro animations"""
    
    def __init__(self, device, font):
        self.device = device
        self.font = font
    
    def tron_grid_flyby(self):
        """Tron-style 3D grid perspective"""
        print("  - TRON grid flyby")
        
        for frame in range(60):
            with canvas(self.device) as draw:
                # Vanishing point at center
                vp_x = 64
                vp_y = 32
                
                # Draw perspective grid lines
                offset = (frame * 4) % 32
                
                # Horizontal lines (floor grid)
                for i in range(10):
                    y = 64 - (i * 6) + offset
                    if y > 32:
                        # Calculate width based on perspective
                        width = int((y - 32) * 2)
                        x1 = vp_x - width
                        x2 = vp_x + width
                        if 0 <= y <= 64:
                            draw.line((x1, y, x2, y), fill="white")
                
                # Vertical lines (perspective)
                for i in range(-3, 4):
                    x_offset = i * 20
                    draw.line((vp_x + x_offset, 64, vp_x + (x_offset // 3), vp_y), fill="white")
                
                # CONNECT text at horizon
                if frame > 20:
                    alpha = min(1.0, (frame - 20) / 20.0)
                    if alpha > 0.5:
                        draw.text((15, 5), "CONNECT", font=self.font, fill="white")
            
            time.sleep(0.04)
    
    def neon_glow_text(self):
        """Neon sign style text with glow effect"""
        print("  - Neon glow effect")
        
        for frame in range(40):
            with canvas(self.device) as draw:
                # Pulsing glow effect (multiple outlines)
                intensity = abs(math.sin(frame * 0.2))
                
                # Draw multiple offset copies for glow
                for offset in range(3, 0, -1):
                    if intensity > (offset * 0.2):
                        for dx in [-offset, 0, offset]:
                            for dy in [-offset, 0, offset]:
                                if dx != 0 or dy != 0:
                                    draw.text((15 + dx, 20 + dy), "CONNECT", font=self.font, fill="white")
                
                # Main text
                draw.text((15, 20), "CONNECT", font=self.font, fill="white")
                
                # Neon tube effect (underline)
                draw.line((15, 35, 113, 35), fill="white", width=2)
                
                # Flickering effect
                if frame % 7 == 0 and random.random() < 0.3:
                    # Skip drawing for flicker
                    pass
            
            time.sleep(0.05)
    
    def scanline_build(self):
        """Old CRT scanline effect building the image"""
        print("  - CRT scanline build")
        
        # Build up with scanlines
        for y in range(0, 64, 2):
            with canvas(self.device) as draw:
                # Draw horizontal scanline
                draw.line((0, y, 127, y), fill="white")
                
                # Draw what's been "scanned" so far
                if y > 10:
                    draw.text((15, 5), "CONNECT", font=self.font, fill="white")
                if y > 25:
                    draw.line((15, 25, 113, 25), fill="white", width=2)
                if y > 40:
                    draw.text((10, 35), "Sensor System", font=self.font, fill="white")
                if y > 55:
                    draw.text((45, 50), "v2.0", font=self.font, fill="white")
            
            time.sleep(0.03)
        
        # Final image with scanlines overlay
        for flash in range(3):
            with canvas(self.device) as draw:
                draw.text((15, 5), "CONNECT", font=self.font, fill="white")
                draw.line((15, 25, 113, 25), fill="white", width=2)
                draw.text((10, 35), "Sensor System", font=self.font, fill="white")
                draw.text((45, 50), "v2.0", font=self.font, fill="white")
                
                # Scanline overlay
                if flash % 2 == 0:
                    for y in range(0, 64, 4):
                        draw.line((0, y, 127, y), fill="white")
            
            time.sleep(0.2)
        
        # Final clean image
        with canvas(self.device) as draw:
            draw.text((15, 5), "CONNECT", font=self.font, fill="white")
            draw.line((15, 25, 113, 25), fill="white", width=2)
            draw.text((10, 35), "Sensor System", font=self.font, fill="white")
            draw.text((45, 50), "v2.0", font=self.font, fill="white")
        
        time.sleep(0.5)
    
    def retro_tunnel(self):
        """Star Wars-style tunnel effect"""
        print("  - Retro tunnel effect")
        
        for frame in range(50):
            with canvas(self.device) as draw:
                # Draw concentric rectangles expanding from center
                for i in range(10):
                    size = ((frame + i * 5) % 50) * 2
                    x = 64 - size
                    y = 32 - (size // 2)
                    
                    if -20 < x < 148 and -20 < y < 84:
                        draw.rectangle((x, y, 64 + size, 32 + (size // 2)), outline="white")
                
                # Logo appears after tunnel starts
                if frame > 25:
                    # Background box for text visibility
                    draw.rectangle((10, 18, 118, 42), fill="black", outline="white")
                    draw.text((15, 22), "CONNECT", font=self.font, fill="white")
            
            time.sleep(0.04)
    
    def vector_wireframe(self):
        """80s vector graphics wireframe cube"""
        print("  - Vector wireframe")
        
        for frame in range(60):
            with canvas(self.device) as draw:
                # Rotating cube in wireframe
                angle = frame * 0.1
                
                # Simple 3D cube vertices
                size = 20
                cx, cy = 35, 32
                
                # Calculate rotation
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                
                # 8 vertices of cube
                vertices = []
                for x in [-1, 1]:
                    for y in [-1, 1]:
                        for z in [-1, 1]:
                            # Rotate
                            rx = x * cos_a - z * sin_a
                            rz = x * sin_a + z * cos_a
                            ry = y
                            
                            # Project to 2D
                            scale = 200 / (200 + rz * size)
                            px = int(cx + rx * size * scale)
                            py = int(cy + ry * size * scale)
                            vertices.append((px, py))
                
                # Draw edges
                edges = [
                    (0, 1), (2, 3), (4, 5), (6, 7),  # Four parallel edges
                    (0, 2), (1, 3), (4, 6), (5, 7),  # Four parallel edges
                    (0, 4), (1, 5), (2, 6), (3, 7)   # Four parallel edges
                ]
                
                for edge in edges:
                    draw.line((vertices[edge[0]][0], vertices[edge[0]][1],
                             vertices[edge[1]][0], vertices[edge[1]][1]), fill="white")
                
                # CONNECT text to the right
                draw.text((75, 12), "CONNECT", font=self.font, fill="white")
                draw.text((75, 28), "Sensor", font=self.font, fill="white")
                draw.text((75, 44), "v2.0", font=self.font, fill="white")
            
            time.sleep(0.04)
    
    def glitch_transition(self):
        """80s digital glitch effect"""
        print("  - Glitch transition")
        
        # Start with filled screen
        with canvas(self.device) as draw:
            draw.rectangle((0, 0, 127, 63), fill="white")
        time.sleep(0.1)
        
        # Glitch breakdown
        for frame in range(30):
            with canvas(self.device) as draw:
                # Random horizontal line displacement
                for y in range(0, 64, 4):
                    offset = random.randint(-10, 10) if random.random() < 0.3 else 0
                    
                    if random.random() < 0.7:
                        draw.line((offset, y, 127 + offset, y), fill="white")
                
                # Random blocks
                for _ in range(5):
                    x = random.randint(0, 120)
                    y = random.randint(0, 60)
                    w = random.randint(4, 20)
                    h = random.randint(2, 10)
                    draw.rectangle((x, y, x + w, y + h), fill="white" if random.random() < 0.5 else "black")
            
            time.sleep(0.05)
        
        # Resolve to CONNECT logo
        for frame in range(20):
            with canvas(self.device) as draw:
                # Less glitchy over time
                if random.random() < (0.5 - frame * 0.025):
                    offset = random.randint(-3, 3)
                    draw.text((15 + offset, 20), "CONNECT", font=self.font, fill="white")
                else:
                    draw.text((15, 20), "CONNECT", font=self.font, fill="white")
                
                draw.line((15, 35, 113, 35), fill="white", width=2)
            
            time.sleep(0.05)
        
        # Clean final
        with canvas(self.device) as draw:
            draw.text((15, 20), "CONNECT", font=self.font, fill="white")
            draw.line((15, 35, 113, 35), fill="white", width=2)
        
        time.sleep(0.5)
    
    def radar_sweep(self):
        """Retro radar sweep animation"""
        print("  - Radar sweep")
        
        cx, cy = 64, 32
        radius = 28
        
        for frame in range(60):
            with canvas(self.device) as draw:
                # Draw radar circles
                for r in range(10, radius + 1, 10):
                    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline="white")
                
                # Draw crosshairs
                draw.line((cx - radius, cy, cx + radius, cy), fill="white")
                draw.line((cx, cy - radius, cx, cy + radius), fill="white")
                
                # Rotating sweep line
                angle = (frame * 12) % 360
                rad = math.radians(angle)
                end_x = cx + int(radius * math.cos(rad))
                end_y = cy + int(radius * math.sin(rad))
                draw.line((cx, cy, end_x, end_y), fill="white")
                
                # Target blips
                if frame > 20:
                    for i in range(3):
                        blip_angle = (i * 120 + frame * 2) % 360
                        blip_rad = math.radians(blip_angle)
                        blip_dist = 15 + (i * 7)
                        bx = cx + int(blip_dist * math.cos(blip_rad))
                        by = cy + int(blip_dist * math.sin(blip_rad))
                        draw.rectangle((bx - 1, by - 1, bx + 1, by + 1), fill="white")
                
                # CONNECT text
                if frame > 30:
                    draw.text((85, 10), "CONNECT", font=self.font, fill="white")
            
            time.sleep(0.04)
    
    def bitmap_reveal(self):
        """Old-school bitmap loading effect"""
        print("  - Bitmap reveal")
        
        # Define CONNECT in a bitmap pattern
        # Each row is 8 pixels tall, we'll draw it column by column
        
        for col in range(128):
            with canvas(self.device) as draw:
                # Draw columns revealed so far
                # Just fill with pattern as we go
                for x in range(0, col, 4):
                    for y in range(0, 64, 4):
                        if (x + y) % 8 == 0:
                            draw.point((x, y), fill="white")
                
                # Show CONNECT text as it's revealed
                if col > 20:
                    draw.text((15, 20), "CONNECT", font=self.font, fill="white")
                if col > 80:
                    draw.line((15, 35, 113, 35), fill="white", width=2)
            
            time.sleep(0.02)
        
        # Final image
        with canvas(self.device) as draw:
            draw.text((15, 20), "CONNECT", font=self.font, fill="white")
            draw.line((15, 35, 113, 35), fill="white", width=2)
        
        time.sleep(0.5)
    
    def run_80s_boot_sequence(self):
        """Run full 80s retro boot sequence"""
        print("Running 80s RETRO boot animation...")
        
        # 1. Tron grid
        self.tron_grid_flyby()
        time.sleep(0.2)
        
        # 2. Vector wireframe
        self.vector_wireframe()
        time.sleep(0.2)
        
        # 3. Radar sweep
        self.radar_sweep()
        time.sleep(0.2)
        
        # 4. Scanline build
        self.scanline_build()
        time.sleep(0.2)
        
        # 5. Final "SYSTEM READY" with scanlines
        for flash in range(5):
            with canvas(self.device) as draw:
                draw.text((20, 10), "CONNECT", font=self.font, fill="white")
                draw.line((20, 25, 108, 25), fill="white", width=2)
                draw.text((15, 35), "SYSTEM READY", font=self.font, fill="white")
                
                # Scanlines
                if flash % 2 == 0:
                    for y in range(0, 64, 3):
                        draw.line((0, y, 127, y), fill="white")
            
            time.sleep(0.2)
        
        # Clean final
        with canvas(self.device) as draw:
            draw.text((20, 10), "CONNECT", font=self.font, fill="white")
            draw.line((20, 25, 108, 25), fill="white", width=2)
            draw.text((15, 35), "SYSTEM READY", font=self.font, fill="white")
        
        time.sleep(1)
        
        print("✓ 80s boot animation complete!")

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
        
        # Run 80s retro boot animation
        boot_anim = Retro80sAnimation(self.device, self.font)
        boot_anim.run_80s_boot_sequence()
        
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
            draw.text((10, 28), "Sensor System", font=self.font, fill="white")
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
        print("CONNECT - 80s RETRO Mode")
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
    print("  80s RETRO MODE - Sensor System v2.0")
    print("  Tron • Vectors • Scanlines • Neon")
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
