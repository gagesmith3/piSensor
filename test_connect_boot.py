#!/usr/bin/env python3
"""
CONNECT - Pi Sensor System Boot Animation
Waveshare 1.3" OLED HAT Display
"""

import time
import sys
from datetime import datetime

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

class ConnectBootAnimation:
    """CONNECT logo boot animation"""
    
    def __init__(self, device, font):
        self.device = device
        self.font = font
    
    def draw_connect_logo_small(self, draw, y_offset=0):
        """Draw a small version of CONNECT logo that fits on 128x64 display"""
        # Small ASCII art version that fits
        logo_lines = [
            " CONNECT",
            "=========",
        ]
        
        y = 10 + y_offset
        for line in logo_lines:
            draw.text((20, y), line, font=self.font, fill="white")
            y += 10
    
    def draw_connect_logo_styled(self, draw, progress=1.0):
        """Draw stylized CONNECT logo with effects"""
        # Draw "CONNECT" in large style with underline
        if progress >= 0.2:
            draw.text((15, 8), "CONNECT", font=self.font, fill="white")
        
        # Draw underline that grows
        if progress >= 0.4:
            line_width = int(98 * min(1.0, (progress - 0.4) / 0.3))
            draw.line((15, 25, 15 + line_width, 25), fill="white", width=2)
        
        # Draw subtitle
        if progress >= 0.7:
            draw.text((15, 35), "Sensor System", font=self.font, fill="white")
        
        # Draw version
        if progress >= 0.9:
            draw.text((45, 50), "v2.0", font=self.font, fill="white")
    
    def sliding_text_animation(self):
        """Slide CONNECT text in from the side"""
        print("  - Sliding logo animation")
        
        for i in range(30):
            progress = i / 29.0
            with canvas(self.device) as draw:
                # Start off-screen right, slide to center
                x_pos = int(128 - (128 - 15) * progress)
                
                draw.text((x_pos, 8), "CONNECT", font=self.font, fill="white")
                
                # Fade in underline
                if progress > 0.5:
                    alpha = (progress - 0.5) * 2
                    line_width = int(98 * alpha)
                    draw.line((15, 25, 15 + line_width, 25), fill="white", width=2)
            
            time.sleep(0.03)
    
    def letter_by_letter_animation(self):
        """Reveal CONNECT one letter at a time"""
        print("  - Letter reveal animation")
        
        text = "CONNECT"
        for i in range(len(text) + 1):
            with canvas(self.device) as draw:
                # Show letters revealed so far
                revealed = text[:i]
                draw.text((15, 20), revealed, font=self.font, fill="white")
                
                # Blinking cursor
                if i < len(text):
                    cursor_x = 15 + (i * 12)  # Approximate character width
                    draw.rectangle((cursor_x, 32, cursor_x + 8, 34), fill="white")
            
            time.sleep(0.15)
        
        # Show final logo with underline
        time.sleep(0.3)
        with canvas(self.device) as draw:
            draw.text((15, 20), "CONNECT", font=self.font, fill="white")
            draw.line((15, 35, 113, 35), fill="white", width=2)
        
        time.sleep(0.5)
    
    def expanding_reveal_animation(self):
        """Expand from center to reveal logo"""
        print("  - Expanding reveal animation")
        
        for i in range(25):
            progress = i / 24.0
            with canvas(self.device) as draw:
                # Expanding box
                width = int(128 * progress)
                height = int(64 * progress)
                x = (128 - width) // 2
                y = (64 - height) // 2
                
                # Draw border
                draw.rectangle((x, y, x + width, y + height), outline="white")
                
                # Reveal logo when box is large enough
                if progress > 0.6:
                    draw.text((15, 20), "CONNECT", font=self.font, fill="white")
                    draw.line((15, 35, 113, 35), fill="white", width=2)
            
            time.sleep(0.04)
    
    def pulse_animation(self):
        """Pulsing CONNECT logo"""
        print("  - Pulse animation")
        
        for cycle in range(3):
            # Expand
            for i in range(10):
                with canvas(self.device) as draw:
                    draw.text((15, 20), "CONNECT", font=self.font, fill="white")
                    draw.line((15, 35, 113, 35), fill="white", width=2)
                    
                    # Expanding box
                    offset = i * 2
                    draw.rectangle((15 - offset, 20 - offset, 
                                  113 + offset, 40 + offset), outline="white")
                time.sleep(0.03)
            
            # Contract
            for i in range(10, 0, -1):
                with canvas(self.device) as draw:
                    draw.text((15, 20), "CONNECT", font=self.font, fill="white")
                    draw.line((15, 35, 113, 35), fill="white", width=2)
                    
                    offset = i * 2
                    draw.rectangle((15 - offset, 20 - offset, 
                                  113 + offset, 40 + offset), outline="white")
                time.sleep(0.03)
        
        # Final static logo
        with canvas(self.device) as draw:
            draw.text((15, 20), "CONNECT", font=self.font, fill="white")
            draw.line((15, 35, 113, 35), fill="white", width=2)
        
        time.sleep(0.3)
    
    def loading_with_logo(self):
        """Loading bar with CONNECT logo above"""
        print("  - Loading sequence")
        
        # Show logo first
        with canvas(self.device) as draw:
            draw.text((15, 5), "CONNECT", font=self.font, fill="white")
            draw.line((15, 20, 113, 20), fill="white", width=1)
        
        time.sleep(0.5)
        
        # Loading bar
        for i in range(101):
            progress = i / 100.0
            with canvas(self.device) as draw:
                # Logo at top
                draw.text((15, 5), "CONNECT", font=self.font, fill="white")
                draw.line((15, 20, 113, 20), fill="white", width=1)
                
                # Loading text
                draw.text((25, 28), "INITIALIZING", font=self.font, fill="white")
                
                # Loading bar
                bar_width = 100
                bar_height = 8
                bar_x = 14
                bar_y = 45
                
                # Border
                draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
                              outline="white")
                
                # Fill
                fill_width = int((bar_width - 2) * progress)
                if fill_width > 0:
                    draw.rectangle((bar_x + 1, bar_y + 1,
                                  bar_x + 1 + fill_width, bar_y + bar_height - 1),
                                  fill="white")
                
                # Percentage
                draw.text((52, 56), f"{i}%", font=self.font, fill="white")
            
            time.sleep(0.02)
        
        time.sleep(0.3)
    
    def system_ready_splash(self):
        """Final 'System Ready' splash screen"""
        print("  - System ready splash")
        
        with canvas(self.device) as draw:
            draw.text((15, 10), "CONNECT", font=self.font, fill="white")
            draw.line((15, 25, 113, 25), fill="white", width=2)
            draw.text((15, 35), "System Ready", font=self.font, fill="white")
            draw.text((48, 50), "v2.0", font=self.font, fill="white")
        
        time.sleep(1.5)
    
    def run_full_boot_sequence(self):
        """Run complete CONNECT boot animation"""
        print("Running CONNECT boot animation...")
        
        # 1. Letter by letter reveal
        self.letter_by_letter_animation()
        
        # 2. Pulse effect
        self.pulse_animation()
        
        # 3. Loading bar
        self.loading_with_logo()
        
        # 4. System ready
        self.system_ready_splash()
        
        print("✓ Boot animation complete!")

class DisplayTest:
    def __init__(self):
        # Initialize GPIO FIRST
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
        
        # Run CONNECT boot animation
        boot_anim = ConnectBootAnimation(self.device, self.font)
        boot_anim.run_full_boot_sequence()
        
        self.button_presses = {k: 0 for k in ['KEY1','KEY2','KEY3','UP','DOWN','LEFT','RIGHT','PRESS']}
        self.last_button = "None"
        self.current_screen = 0
        self.test_counter = 0
        
        # Button state tracking for polling
        self.button_states = {}
        self.pin_map = {
            KEY1_PIN: 'KEY1',
            KEY2_PIN: 'KEY2',
            KEY3_PIN: 'KEY3',
            JOYSTICK_UP: 'UP',
            JOYSTICK_DOWN: 'DOWN',
            JOYSTICK_LEFT: 'LEFT',
            JOYSTICK_RIGHT: 'RIGHT',
            JOYSTICK_PRESS: 'PRESS'
        }
        
        # Initialize button states
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
        print("CONNECT - Sensor System Running")
        print("="*60)
        print("\nControls:")
        print("  LEFT/RIGHT  - Navigate screens")
        print("  UP/DOWN     - Increment/Decrement counter")
        print("  PRESS       - Reset counter")
        print("  KEY1/2/3    - Test buttons")
        print("  Ctrl+C      - Exit test")
        print("\n" + "="*60 + "\n")
        
        try:
            frame_count = 0
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
    print("  Sensor System v2.0 - Raspberry Pi 3B")
    print("="*60 + "\n")
    
    try:
        test = DisplayTest()
        test.run_test()
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    main()
