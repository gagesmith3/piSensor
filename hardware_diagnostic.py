#!/usr/bin/env python3
"""
Hardware diagnostic for Waveshare OLED HAT
Checks for common hardware issues
"""

import time
import sys

print("\n" + "="*60)
print("  HARDWARE DIAGNOSTIC CHECKLIST")
print("="*60)

# Check 1: Display import
print("\n[1] Checking display library...")
try:
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    print("✓ Libraries imported successfully")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Check 2: SPI devices
print("\n[2] Checking SPI devices...")
import os
spi_devices = ['/dev/spidev0.0', '/dev/spidev0.1']
for dev in spi_devices:
    if os.path.exists(dev):
        print(f"✓ Found {dev}")
    else:
        print(f"✗ Missing {dev}")

# Check 3: Initialize display
print("\n[3] Initializing display...")
try:
    serial = spi(device=0, port=0, bus_speed_hz=8000000, dc_pin=24, rst_pin=25)
    device = sh1106(serial, rotate=2)
    print(f"✓ Display initialized: {device.width}x{device.height}")
except Exception as e:
    print(f"✗ Initialization failed: {e}")
    sys.exit(1)

# Check 4: Contrast test
print("\n[4] Testing MAXIMUM CONTRAST...")
print("Setting contrast to 255 (maximum brightness)...")
try:
    device.contrast(255)
    print("✓ Contrast set to MAX")
except Exception as e:
    print(f"✗ Failed: {e}")

# Check 5: Full brightness pattern
print("\n[5] Drawing FULL WHITE screen with MAX brightness...")
print("*** LOOK AT YOUR DISPLAY NOW ***")
print("You should see a BRIGHT WHITE screen!")

for i in range(10):
    print(f"  Attempt {i+1}/10 - WHITE")
    with canvas(device) as draw:
        # Fill entire screen with white
        draw.rectangle((0, 0, 127, 63), outline="white", fill="white")
    time.sleep(0.5)
    
    print(f"  Attempt {i+1}/10 - BLACK")
    with canvas(device) as draw:
        draw.rectangle((0, 0, 127, 63), outline="black", fill="black")
    time.sleep(0.5)

# Check 6: Power commands
print("\n[6] Testing display ON/OFF commands...")
try:
    print("Display OFF...")
    device.hide()
    time.sleep(1)
    
    print("Display ON...")
    device.show()
    time.sleep(1)
    print("✓ ON/OFF commands executed")
except Exception as e:
    print(f"✗ Failed: {e}")

# Check 7: Draw test pattern
print("\n[7] Drawing test pattern...")
with canvas(device) as draw:
    # Border
    draw.rectangle((0, 0, 127, 63), outline="white", fill="black")
    # Cross
    draw.line((0, 0, 127, 63), fill="white", width=2)
    draw.line((127, 0, 0, 63), fill="white", width=2)
    # Center box
    draw.rectangle((40, 20, 87, 43), outline="white", fill="white")

print("*** CHECK YOUR DISPLAY ***")
print("You should see:")
print("  - White border around edge")
print("  - White X across screen")  
print("  - White rectangle in center")

time.sleep(5)

# Final questions
print("\n" + "="*60)
print("  DIAGNOSTIC QUESTIONS")
print("="*60)
print("\nPlease answer these questions:")
print()
print("1. Did you see ANYTHING on the display during this test?")
print("   - Any flicker, glow, dots, or changes?")
print()
print("2. Is there a protective film/sticker on the display?")
print("   - Check for a plastic film covering the screen")
print()
print("3. Can you see the display pixels when OFF?")
print("   - Look closely - are there tiny dark squares visible?")
print()
print("4. Is the display backlit or reflective?")
print("   - OLED = self-lit (glows in dark)")
print("   - E-paper = needs light to see")
print()
print("5. What color is the display supposed to be?")
print("   - White/Blue on black background?")
print()
print("6. Is the HAT seated firmly on ALL 40 GPIO pins?")
print("   - Check both sides of the board")
print()
print("7. Do you have another Pi to test the HAT on?")
print()
print("8. Can you take a photo of the display and HAT?")
print()
print("="*60)

# Clear display
with canvas(device) as draw:
    draw.rectangle((0, 0, 127, 63), outline="black", fill="black")

print("\nDiagnostic complete.")
