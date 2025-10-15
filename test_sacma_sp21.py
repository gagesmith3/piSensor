#!/usr/bin/env python3
"""
CONNECT - Sacma SP-21 Heading Machine Animation
Accurate horizontal cold heading machine visualization
Based on Sacma SP-21 multi-station design
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

class SacmaSP21Animation:
    """Sacma SP-21 horizontal cold heading machine animation"""
    
    def __init__(self, device, font):
        self.device = device
        self.font = font
    
    def draw_machine_base(self, draw):
        """Draw the Sacma SP-21 machine base and frame (horizontal design)"""
        # Machine bed/base (horizontal)
        draw.rectangle((5, 48, 123, 58), outline="white", fill="black")
        
        # Frame supports
        draw.rectangle((10, 35, 15, 48), outline="white")
        draw.rectangle((60, 35, 65, 48), outline="white")
        draw.rectangle((108, 35, 113, 48), outline="white")
    
    def draw_wire_straightener_feed(self, draw, feed_position):
        """
        Draw wire straightener and feed mechanism (Sacma uses straightener rollers)
        feed_position: 0 to 1
        """
        # Wire straightener housing (left side)
        draw.rectangle((5, 20, 15, 35), outline="white")
        draw.text((6, 23), "WS", font=self.font, fill="white")  # Wire Straightener
        
        # Straightener rollers (simplified)
        roller_y = 27
        for i in range(3):
            y = roller_y + (i * 3)
            draw.ellipse((8, y, 12, y + 2), outline="white")
        
        # Wire coming out of straightener
        wire_start_x = 15
        wire_y = 27
        wire_end_x = 15 + int(25 * feed_position)
        
        if wire_end_x > wire_start_x:
            draw.line((wire_start_x, wire_y, wire_end_x, wire_y), fill="white", width=2)
        
        # Feed grip mechanism
        grip_x = 38
        grip_open = 3 if feed_position < 0.5 else 1
        draw.rectangle((grip_x, wire_y - grip_open, grip_x + 4, wire_y + grip_open), outline="white")
    
    def draw_horizontal_punch_die(self, draw, punch_position, station=1):
        """
        Draw horizontal punch and die mechanism (key feature of Sacma)
        punch_position: 0 (retracted) to 1 (forward/striking)
        station: 1 or 2 for multi-blow
        """
        # Station position
        base_x = 45 if station == 1 else 75
        center_y = 27
        
        # Die block (stationary)
        die_x = base_x + 5
        draw.rectangle((die_x, center_y - 4, die_x + 8, center_y + 4), outline="white", fill="black")
        draw.text((die_x + 1, center_y - 2), "D", font=self.font, fill="white")
        
        # Punch (moves horizontally)
        punch_travel = 12
        punch_x = base_x - 15 + int(punch_travel * punch_position)
        punch_width = 10
        
        # Punch body
        draw.rectangle((punch_x, center_y - 3, punch_x + punch_width, center_y + 3), outline="white", fill="black")
        
        # Punch tip (striking end)
        draw.line((punch_x + punch_width, center_y - 2, 
                  punch_x + punch_width + 2, center_y - 2), fill="white", width=2)
        draw.line((punch_x + punch_width, center_y + 2,
                  punch_x + punch_width + 2, center_y + 2), fill="white", width=2)
        
        # Strike indication
        if punch_position > 0.85:
            # Impact lines
            for offset in [1, 2]:
                draw.line((die_x - offset, center_y - 5,
                          die_x - offset, center_y - 7), fill="white")
                draw.line((die_x - offset, center_y + 5,
                          die_x - offset, center_y + 7), fill="white")
        
        # Punch drive mechanism
        draw.line((punch_x, center_y, punch_x - 5, center_y), fill="white")
    
    def draw_workpiece_at_station(self, draw, station, forming_stage):
        """
        Draw the workpiece at different forming stages
        station: 1=first blow, 2=second blow
        forming_stage: 0 to 1
        """
        base_x = 50 if station == 1 else 80
        y = 27
        
        if station == 1:
            # First blow - partial head
            # Wire body
            draw.line((base_x - 5, y, base_x + 5, y), fill="white", width=2)
            
            if forming_stage > 0.3:
                # Partial head forming
                head_size = int(3 * forming_stage)
                draw.rectangle((base_x - head_size, y - 2,
                              base_x + head_size, y + 2), outline="white")
        
        elif station == 2:
            # Second blow - full head
            # Wire body
            draw.line((base_x - 5, y, base_x + 5, y), fill="white", width=2)
            
            if forming_stage > 0.5:
                # Full head
                draw.rectangle((base_x - 4, y - 3,
                              base_x + 4, y + 3), fill="white", outline="white")
    
    def draw_transfer_mechanism(self, draw, transfer_position):
        """
        Draw the transfer fingers that move parts between stations
        transfer_position: 0 to 1
        """
        # Transfer fingers move in an arc from station 1 to station 2
        start_x = 55
        end_x = 85
        
        # Finger position
        finger_x = start_x + int((end_x - start_x) * transfer_position)
        finger_y = 22 - int(5 * math.sin(transfer_position * math.pi))  # Arc motion
        
        # Transfer finger
        draw.rectangle((finger_x - 2, finger_y, finger_x + 2, finger_y + 3), outline="white")
        
        # Connection to drive
        draw.line((finger_x, finger_y, finger_x, 18), fill="white")
    
    def draw_cutoff_mechanism(self, draw, cutoff_position):
        """
        Draw the cutoff/trimming mechanism
        cutoff_position: 0 (open) to 1 (cutting)
        """
        # Cutoff position (after station 2)
        cutoff_x = 100
        cutoff_y = 27
        
        # Shear blade movement
        blade_travel = int(8 * cutoff_position)
        
        # Upper blade
        draw.line((cutoff_x, cutoff_y - 4 + blade_travel,
                  cutoff_x + 6, cutoff_y - 4 + blade_travel), fill="white", width=2)
        
        # Lower blade (stationary)
        draw.line((cutoff_x, cutoff_y + 4,
                  cutoff_x + 6, cutoff_y + 4), fill="white", width=2)
        
        # Cutting in progress
        if 0.3 < cutoff_position < 0.7:
            draw.text((cutoff_x - 8, cutoff_y - 8), "CUT", font=self.font, fill="white")
    
    def sacma_production_cycle(self):
        """Animate one complete Sacma SP-21 production cycle"""
        print("  - Sacma SP-21 production cycle")
        
        frames = 80
        
        for frame in range(frames):
            progress = frame / (frames - 1)
            
            with canvas(self.device) as draw:
                # Machine base
                self.draw_machine_base(draw)
                
                # Title
                draw.text((2, 2), "SACMA SP-21", font=self.font, fill="white")
                
                # Cycle phases
                cycle_phase = int(progress * 6) % 6
                
                # Phase 0: Wire feed
                if cycle_phase == 0:
                    phase_progress = (progress * 6) % 1
                    self.draw_wire_straightener_feed(draw, phase_progress)
                    draw.text((95, 2), "FEED", font=self.font, fill="white")
                
                # Phase 1: Station 1 punch (first blow)
                elif cycle_phase == 1:
                    phase_progress = (progress * 6) % 1
                    self.draw_wire_straightener_feed(draw, 1)
                    self.draw_horizontal_punch_die(draw, phase_progress, station=1)
                    self.draw_workpiece_at_station(draw, 1, phase_progress)
                    draw.text((90, 2), "BLOW 1", font=self.font, fill="white")
                
                # Phase 2: Transfer to station 2
                elif cycle_phase == 2:
                    phase_progress = (progress * 6) % 1
                    self.draw_wire_straightener_feed(draw, 1)
                    self.draw_horizontal_punch_die(draw, 0, station=1)
                    self.draw_horizontal_punch_die(draw, 0, station=2)
                    self.draw_transfer_mechanism(draw, phase_progress)
                    draw.text((85, 2), "TRANSFER", font=self.font, fill="white")
                
                # Phase 3: Station 2 punch (second blow)
                elif cycle_phase == 3:
                    phase_progress = (progress * 6) % 1
                    self.draw_wire_straightener_feed(draw, 1)
                    self.draw_horizontal_punch_die(draw, 0, station=1)
                    self.draw_horizontal_punch_die(draw, phase_progress, station=2)
                    self.draw_workpiece_at_station(draw, 2, phase_progress)
                    draw.text((90, 2), "BLOW 2", font=self.font, fill="white")
                
                # Phase 4: Cutoff
                elif cycle_phase == 4:
                    phase_progress = (progress * 6) % 1
                    self.draw_wire_straightener_feed(draw, 0)
                    self.draw_horizontal_punch_die(draw, 0, station=1)
                    self.draw_horizontal_punch_die(draw, 0, station=2)
                    self.draw_cutoff_mechanism(draw, phase_progress)
                    draw.text((95, 2), "CUT", font=self.font, fill="white")
                
                # Phase 5: Eject
                elif cycle_phase == 5:
                    phase_progress = (progress * 6) % 1
                    self.draw_wire_straightener_feed(draw, 0)
                    self.draw_horizontal_punch_die(draw, 0, station=1)
                    self.draw_horizontal_punch_die(draw, 0, station=2)
                    
                    # Ejected part
                    eject_x = 105 + int(15 * phase_progress)
                    eject_y = 27 + int(10 * phase_progress)
                    if eject_x < 127:
                        draw.line((eject_x - 3, eject_y, eject_x + 3, eject_y), fill="white", width=2)
                        draw.rectangle((eject_x - 2, eject_y - 2,
                                      eject_x + 2, eject_y + 2), fill="white")
                    
                    draw.text((90, 2), "EJECT", font=self.font, fill="white")
            
            time.sleep(0.06)
    
    def continuous_sacma_production(self):
        """Continuous production with cycle counter"""
        print("  - Continuous production mode")
        
        parts_count = 0
        
        for cycle in range(3):
            for frame in range(40):
                progress = frame / 39.0
                
                with canvas(self.device) as draw:
                    self.draw_machine_base(draw)
                    
                    # Synchronized motion
                    # Punches alternate
                    punch1_pos = abs(math.sin(progress * math.pi * 2))
                    punch2_pos = abs(math.sin((progress + 0.5) * math.pi * 2))
                    
                    self.draw_wire_straightener_feed(draw, (progress * 4) % 1)
                    self.draw_horizontal_punch_die(draw, punch1_pos, station=1)
                    self.draw_horizontal_punch_die(draw, punch2_pos, station=2)
                    
                    # Production counter
                    draw.text((2, 2), f"SP-21: {parts_count}", font=self.font, fill="white")
                    draw.text((80, 2), "RUNNING", font=self.font, fill="white")
                
                time.sleep(0.04)
            
            parts_count += 1
    
    def run_sacma_boot_sequence(self):
        """Complete Sacma SP-21 boot sequence"""
        print("Running Sacma SP-21 boot animation...")
        
        # 1. Machine identification
        with canvas(self.device) as draw:
            draw.text((25, 10), "SACMA", font=self.font, fill="white")
            draw.text((25, 25), "SP-21", font=self.font, fill="white")
            draw.text((10, 40), "Cold Heading", font=self.font, fill="white")
        time.sleep(1.5)
        
        # 2. Single cycle demo
        self.sacma_production_cycle()
        time.sleep(0.3)
        
        # 3. Continuous production
        self.continuous_sacma_production()
        time.sleep(0.3)
        
        # 4. System ready
        with canvas(self.device) as draw:
            draw.text((20, 5), "CONNECT", font=self.font, fill="white")
            draw.line((20, 20, 108, 20), fill="white", width=2)
            draw.text((15, 28), "Sacma SP-21", font=self.font, fill="white")
            draw.text((20, 42), "System Ready", font=self.font, fill="white")
            draw.text((48, 54), "v2.0", font=self.font, fill="white")
        
        time.sleep(1.5)
        
        print("✓ Sacma SP-21 boot complete!")

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
        
        # Run Sacma SP-21 boot animation
        boot_anim = SacmaSP21Animation(self.device, self.font)
        boot_anim.run_sacma_boot_sequence()
        
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
    
    def draw_rotating_weld_stud(self, draw, angle):
        """Animated rotating weld stud for home screen"""
        # Simplified 3D weld stud (compact version for corner)
        center_x, center_y = 110, 12
        
        # Rotation matrix
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Simple weld stud vertices (head, shaft, point)
        vertices_3d = [
            # Head (wider)
            (-3, -1, -1), (3, -1, -1), (3, -1, 1), (-3, -1, 1),
            (-3, 1, -1), (3, 1, -1), (3, 1, 1), (-3, 1, 1),
            # Shaft
            (-1.5, 1, -1), (1.5, 1, -1), (1.5, 1, 1), (-1.5, 1, 1),
            (-1.5, 4, -1), (1.5, 4, -1), (1.5, 4, 1), (-1.5, 4, 1),
        ]
        
        # Rotate and project
        projected = []
        for x, y, z in vertices_3d:
            # Rotate around Y axis
            rx = x * cos_a - z * sin_a
            rz = x * sin_a + z * cos_a
            # Simple perspective
            scale = 1.5 / (1 + rz * 0.05)
            sx = center_x + int(rx * scale)
            sy = center_y + int(y * scale)
            projected.append((sx, sy))
        
        # Draw edges (simplified wireframe)
        edges = [(0,1),(1,2),(2,3),(3,0), (4,5),(5,6),(6,7),(7,4),
                 (0,4),(1,5),(2,6),(3,7), (8,9),(9,10),(10,11),(11,8),
                 (12,13),(13,14),(14,15),(15,12), (8,12),(9,13),(10,14),(11,15),
                 (4,8),(5,9),(6,10),(7,11)]
        
        for i, j in edges:
            if i < len(projected) and j < len(projected):
                try:
                    draw.line((projected[i][0], projected[i][1],
                             projected[j][0], projected[j][1]), fill="white")
                except:
                    pass
    
    def draw_machine_mini_animation(self, draw, frame):
        """Mini SP-21 punch animation for system info screen"""
        # Compact version in top-right corner
        base_x, base_y = 90, 8
        
        # Punch position (oscillates)
        punch_pos = abs(math.sin(frame * 0.2))
        
        # Die
        draw.rectangle((base_x + 10, base_y - 2, base_x + 14, base_y + 2), outline="white")
        
        # Punch (horizontal movement)
        punch_x = base_x + int(8 * punch_pos)
        draw.rectangle((punch_x, base_y - 1, punch_x + 6, base_y + 1), outline="white", fill="black")
        
        # Strike indicator
        if punch_pos > 0.8:
            draw.line((base_x + 12, base_y - 3, base_x + 12, base_y - 5), fill="white")
            draw.line((base_x + 12, base_y + 3, base_x + 12, base_y + 5), fill="white")
    
    def draw_button_pulse(self, draw, frame, btn_name):
        """Pulsing button indicator for button test screen"""
        # Shows which button was last pressed with a pulse
        positions = {
            'KEY1': (100, 25), 'KEY2': (100, 37), 'KEY3': (100, 49),
        }
        
        if btn_name in positions:
            x, y = positions[btn_name]
            pulse = abs(math.sin(frame * 0.3))
            size = 2 + int(2 * pulse)
            draw.ellipse((x - size, y - size, x + size, y + size), outline="white", fill="white")
    
    def draw_joystick_direction(self, draw, frame, direction):
        """Animated joystick direction indicator"""
        center_x, center_y = 110, 30
        
        # Pulsing arrow in direction
        pulse = abs(math.sin(frame * 0.3))
        offset = 8 + int(3 * pulse)
        
        if direction == 'UP':
            draw.line((center_x, center_y - offset, center_x, center_y - offset - 5), fill="white", width=2)
            draw.line((center_x, center_y - offset - 5, center_x - 2, center_y - offset - 3), fill="white")
            draw.line((center_x, center_y - offset - 5, center_x + 2, center_y - offset - 3), fill="white")
        elif direction == 'DOWN':
            draw.line((center_x, center_y + offset, center_x, center_y + offset + 5), fill="white", width=2)
            draw.line((center_x, center_y + offset + 5, center_x - 2, center_y + offset + 3), fill="white")
            draw.line((center_x, center_y + offset + 5, center_x + 2, center_y + offset + 3), fill="white")
        elif direction == 'LEFT':
            draw.line((center_x - offset, center_y, center_x - offset - 5, center_y), fill="white", width=2)
            draw.line((center_x - offset - 5, center_y, center_x - offset - 3, center_y - 2), fill="white")
            draw.line((center_x - offset - 5, center_y, center_x - offset - 3, center_y + 2), fill="white")
        elif direction == 'RIGHT':
            draw.line((center_x + offset, center_y, center_x + offset + 5, center_y), fill="white", width=2)
            draw.line((center_x + offset + 5, center_y, center_x + offset + 3, center_y - 2), fill="white")
            draw.line((center_x + offset + 5, center_y, center_x + offset + 3, center_y + 2), fill="white")
        elif direction == 'PRESS':
            # Circle pulsing
            radius = 3 + int(3 * pulse)
            draw.ellipse((center_x - radius, center_y - radius,
                         center_x + radius, center_y + radius), outline="white", fill="black")
            draw.ellipse((center_x - 1, center_y - 1,
                         center_x + 1, center_y + 1), fill="white")
    
    def draw_screen_0(self):
        """Home screen with rotating weld stud animation"""
        with canvas(self.device) as draw:
            draw.text((20, 5), "CONNECT", font=self.font, fill="white")
            draw.line((20, 20, 108, 20), fill="white", width=1)
            draw.text((15, 28), "Sacma SP-21", font=self.font, fill="white")
            draw.text((0, 45), "Use <- -> navigate", font=self.font, fill="white")
            
            # Animated rotating weld stud in corner
            angle = time.time() * 2
            self.draw_rotating_weld_stud(draw, angle)
    
    def draw_screen_1(self):
        """System info screen with mini punch animation"""
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
            
            # Mini SP-21 punch animation
            self.draw_machine_mini_animation(draw, time.time() * 10)
    
    def draw_screen_2(self):
        """Button test screen with pulsing indicators"""
        with canvas(self.device) as draw:
            draw.text((0, 0), "=== BUTTON TEST ===", font=self.font, fill="white")
            draw.text((0, 12), f"Last: {self.last_button}", font=self.font, fill="white")
            y = 25
            for btn in ['KEY1', 'KEY2', 'KEY3']:
                count = self.button_presses[btn]
                draw.text((0, y), f"{btn}: {count}", font=self.font, fill="white")
                y += 12
            
            # Pulsing indicator for last pressed button
            if self.last_button in ['KEY1', 'KEY2', 'KEY3']:
                self.draw_button_pulse(draw, time.time() * 10, self.last_button)
    
    def draw_screen_3(self):
        """Joystick test screen with direction animation"""
        with canvas(self.device) as draw:
            draw.text((0, 0), "== JOYSTICK TEST ==", font=self.font, fill="white")
            y = 12
            for btn in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'PRESS']:
                count = self.button_presses[btn]
                draw.text((0, y), f"{btn}: {count}", font=self.font, fill="white")
                y += 10
            
            # Animated direction indicator for last joystick input
            if self.last_button in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'PRESS']:
                self.draw_joystick_direction(draw, time.time() * 10, self.last_button)
    
    def run_test(self):
        print("\n" + "="*60)
        print("CONNECT - Sacma SP-21 Sensor System")
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
    print("  SACMA SP-21 SENSOR - Factory Accurate v2.0")
    print("  Horizontal Cold Heading Machine")
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
