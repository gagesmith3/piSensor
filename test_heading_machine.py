#!/usr/bin/env python3
"""
CONNECT - 3D Screw Heading Machine Animation
Animated industrial heading machine with moving parts
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

class HeadingMachineAnimation:
    """3D animated screw heading machine"""
    
    def __init__(self, device, font):
        self.device = device
        self.font = font
    
    def draw_machine_frame(self, draw):
        """Draw the static frame/body of the heading machine"""
        # Machine base (wide rectangular base)
        draw.rectangle((10, 50, 118, 60), outline="white", fill="black")
        draw.line((10, 50, 5, 55), fill="white")  # 3D effect left
        draw.line((118, 50, 123, 55), fill="white")  # 3D effect right
        draw.line((5, 55, 5, 63), fill="white")
        draw.line((123, 55, 123, 63), fill="white")
        draw.line((5, 63, 10, 60), fill="white")
        draw.line((123, 63, 118, 60), fill="white")
        
        # Vertical support columns
        draw.rectangle((20, 30, 24, 50), outline="white")
        draw.rectangle((104, 30, 108, 50), outline="white")
        
        # Top beam
        draw.rectangle((20, 25, 108, 30), outline="white")
        draw.line((20, 25, 16, 22), fill="white")
        draw.line((108, 25, 112, 22), fill="white")
        draw.line((16, 22, 112, 22), fill="white")
    
    def draw_ram_assembly(self, draw, position):
        """
        Draw the ram (punch/die assembly) that moves down to form heads
        position: 0 (top) to 1 (bottom/striking)
        """
        # Ram moves vertically
        base_y = 30
        travel = 15
        current_y = base_y + int(position * travel)
        
        # Ram block (the striking component)
        ram_left = 55
        ram_right = 73
        ram_top = current_y
        ram_bottom = current_y + 8
        
        # Main ram body
        draw.rectangle((ram_left, ram_top, ram_right, ram_bottom), outline="white", fill="black")
        
        # Ram guide rods (vertical shafts)
        draw.line((50, 30, 50, current_y), fill="white")
        draw.line((78, 30, 78, current_y), fill="white")
        
        # Die face (bottom of ram)
        draw.line((ram_left, ram_bottom, ram_right, ram_bottom), fill="white", width=2)
        
        # Strike indication when at bottom
        if position > 0.8:
            # Flash/impact lines
            for offset in [2, 4, 6]:
                draw.line((ram_left - offset, ram_bottom + 2, 
                          ram_left - offset - 3, ram_bottom + 5), fill="white")
                draw.line((ram_right + offset, ram_bottom + 2,
                          ram_right + offset + 3, ram_bottom + 5), fill="white")
    
    def draw_wire_feed(self, draw, feed_position):
        """
        Draw the wire feed mechanism
        feed_position: 0 to 1, shows wire advancing
        """
        # Wire feed tube
        draw.rectangle((85, 42, 100, 46), outline="white")
        
        # Wire stock inside feed
        wire_length = int(15 * feed_position)
        if wire_length > 0:
            draw.line((85, 44, 85 - wire_length, 44), fill="white", width=2)
        
        # Feed rollers (rotating)
        angle = feed_position * 360
        roller_x = 88
        roller_y = 44
        roller_r = 3
        
        # Simple rotating indicator
        rad = math.radians(angle)
        end_x = roller_x + int(roller_r * math.cos(rad))
        end_y = roller_y + int(roller_r * math.sin(rad))
        
        draw.ellipse((roller_x - roller_r, roller_y - roller_r,
                     roller_x + roller_r, roller_y + roller_r), outline="white")
        draw.line((roller_x, roller_y, end_x, end_y), fill="white")
    
    def draw_workpiece(self, draw, stage):
        """
        Draw the workpiece (stud being formed)
        stage: 0=blank wire, 0.5=forming, 1=complete stud
        """
        # Position where work happens
        work_x = 64
        work_y = 48
        
        if stage < 0.3:
            # Blank wire segment
            draw.line((work_x - 5, work_y, work_x + 5, work_y), fill="white", width=2)
        elif stage < 0.7:
            # Forming - wire with partial head
            draw.line((work_x - 5, work_y, work_x + 5, work_y), fill="white", width=2)
            # Partial head forming
            head_width = int(8 * ((stage - 0.3) / 0.4))
            draw.rectangle((work_x - head_width, work_y - 2,
                          work_x + head_width, work_y + 2), outline="white")
        else:
            # Complete stud with head
            # Shaft
            draw.line((work_x - 5, work_y, work_x + 5, work_y), fill="white", width=2)
            # Head
            draw.rectangle((work_x - 4, work_y - 3,
                          work_x + 4, work_y + 3), fill="white", outline="white")
    
    def draw_cutting_mechanism(self, draw, cut_position):
        """
        Draw the cutoff mechanism that cuts finished studs
        cut_position: 0 (open) to 1 (closed/cutting)
        """
        # Shear blades
        blade_y = 48
        blade_gap = 15 - int(14 * cut_position)
        
        # Upper blade
        draw.line((70, blade_y - blade_gap, 80, blade_y - blade_gap), fill="white", width=2)
        # Lower blade
        draw.line((70, blade_y + blade_gap, 80, blade_y + blade_gap), fill="white", width=2)
        
        # Shear guides
        draw.line((70, blade_y - blade_gap, 70, blade_y - 8), fill="white")
        draw.line((70, blade_y + blade_gap, 70, blade_y + 8), fill="white")
    
    def heading_machine_cycle_animation(self):
        """Animate one complete heading machine cycle"""
        print("  - Heading machine cycle animation")
        
        # One complete machine cycle: feed -> form -> cut -> eject
        frames_per_stage = 20
        total_frames = frames_per_stage * 4
        
        for frame in range(total_frames):
            progress = frame / total_frames
            stage = int(frame / frames_per_stage)
            stage_progress = (frame % frames_per_stage) / frames_per_stage
            
            with canvas(self.device) as draw:
                # Always draw machine frame
                self.draw_machine_frame(draw)
                
                # Stage 0: Wire feed
                if stage == 0:
                    self.draw_wire_feed(draw, stage_progress)
                    self.draw_workpiece(draw, 0)
                    self.draw_ram_assembly(draw, 0)
                    draw.text((2, 2), "FEED", font=self.font, fill="white")
                
                # Stage 1: Ram down + forming
                elif stage == 1:
                    self.draw_wire_feed(draw, 1)
                    self.draw_ram_assembly(draw, stage_progress)
                    self.draw_workpiece(draw, stage_progress)
                    draw.text((2, 2), "FORM", font=self.font, fill="white")
                
                # Stage 2: Ram up + cutting
                elif stage == 2:
                    self.draw_wire_feed(draw, 1)
                    self.draw_ram_assembly(draw, 1 - stage_progress)
                    self.draw_workpiece(draw, 1)
                    self.draw_cutting_mechanism(draw, stage_progress)
                    draw.text((2, 2), "CUT", font=self.font, fill="white")
                
                # Stage 3: Eject + reset
                elif stage == 3:
                    self.draw_wire_feed(draw, 0)
                    self.draw_ram_assembly(draw, 0)
                    # Show stud ejecting
                    eject_x = 64 + int(stage_progress * 30)
                    eject_y = 48 + int(stage_progress * 10)
                    if eject_x < 127:
                        # Ejected stud
                        draw.line((eject_x - 5, eject_y, eject_x + 5, eject_y), fill="white", width=2)
                        draw.rectangle((eject_x - 4, eject_y - 3,
                                      eject_x + 4, eject_y + 3), fill="white")
                    draw.text((2, 2), "EJECT", font=self.font, fill="white")
                
                # Cycle counter
                draw.text((100, 2), f"#{frame//frames_per_stage + 1}", font=self.font, fill="white")
            
            time.sleep(0.05)
    
    def continuous_production_animation(self):
        """Show continuous production with counter"""
        print("  - Continuous production animation")
        
        parts_made = 0
        
        for cycle in range(5):
            # Fast production cycle
            for frame in range(40):
                progress = frame / 39.0
                
                with canvas(self.device) as draw:
                    # Simplified continuous animation
                    self.draw_machine_frame(draw)
                    
                    # Ram cycles
                    ram_pos = abs(math.sin(progress * math.pi * 2))
                    self.draw_ram_assembly(draw, ram_pos)
                    
                    # Wire feed pulses
                    feed_pos = (progress * 4) % 1
                    self.draw_wire_feed(draw, feed_pos)
                    
                    # Workpiece
                    work_stage = (progress * 2) % 1
                    self.draw_workpiece(draw, work_stage)
                    
                    # Production counter
                    draw.text((2, 2), "PRODUCTION", font=self.font, fill="white")
                    draw.text((2, 14), f"Count: {parts_made}", font=self.font, fill="white")
                    
                    # Speed indicator
                    draw.text((85, 2), f"{int(progress*100)}%", font=self.font, fill="white")
                
                time.sleep(0.04)
            
            parts_made += 1
        
        time.sleep(0.3)
    
    def machine_startup_sequence(self):
        """Show machine powering up"""
        print("  - Machine startup sequence")
        
        for frame in range(40):
            progress = frame / 39.0
            
            with canvas(self.device) as draw:
                # Build machine piece by piece
                if progress > 0.2:
                    # Base appears
                    draw.rectangle((10, 50, 118, 60), outline="white", fill="black")
                
                if progress > 0.4:
                    # Columns
                    draw.rectangle((20, 30, 24, 50), outline="white")
                    draw.rectangle((104, 30, 108, 50), outline="white")
                
                if progress > 0.6:
                    # Top beam
                    draw.rectangle((20, 25, 108, 30), outline="white")
                
                if progress > 0.7:
                    # Ram assembly
                    self.draw_ram_assembly(draw, 0)
                
                if progress > 0.8:
                    # Wire feed
                    self.draw_wire_feed(draw, 0)
                
                # Startup text
                draw.text((20, 10), "STARTING UP", font=self.font, fill="white")
                
                # Progress bar
                bar_width = int(80 * progress)
                draw.rectangle((24, 18, 104, 22), outline="white")
                if bar_width > 0:
                    draw.rectangle((25, 19, 25 + bar_width, 21), fill="white")
            
            time.sleep(0.05)
        
        # System ready
        with canvas(self.device) as draw:
            self.draw_machine_frame(draw)
            self.draw_ram_assembly(draw, 0)
            self.draw_wire_feed(draw, 0)
            draw.text((30, 10), "READY", font=self.font, fill="white")
        
        time.sleep(0.5)
    
    def run_heading_machine_boot(self):
        """Run complete heading machine boot sequence"""
        print("Running heading machine boot animation...")
        
        # 1. Startup
        self.machine_startup_sequence()
        
        # 2. Single cycle demonstration
        self.heading_machine_cycle_animation()
        
        # 3. Continuous production
        self.continuous_production_animation()
        
        # 4. Final splash
        with canvas(self.device) as draw:
            draw.text((20, 5), "CONNECT", font=self.font, fill="white")
            draw.line((20, 20, 108, 20), fill="white", width=2)
            draw.text((5, 28), "Heading Machine", font=self.font, fill="white")
            draw.text((20, 42), "System Ready", font=self.font, fill="white")
            draw.text((48, 54), "v2.0", font=self.font, fill="white")
        
        time.sleep(1.5)
        
        print("✓ Heading machine boot complete!")

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
        
        # Run heading machine boot animation
        boot_anim = HeadingMachineAnimation(self.device, self.font)
        boot_anim.run_heading_machine_boot()
        
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
            draw.text((0, 28), "Heading Machine", font=self.font, fill="white")
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
        print("CONNECT - Heading Machine Sensor System")
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
    print("  HEADING MACHINE SENSOR - Industrial Edition v2.0")
    print("  Animated Production Cycle Visualization")
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
