#!/usr/bin/env python3
"""
Simple Display Test - No GPIO buttons, just display
Tests different display configurations to find what works
"""

import time
import sys
from datetime import datetime

try:
    from luma.core.interface.serial import spi, i2c
    from luma.core.render import canvas
    from luma.oled.device import sh1106, ssd1306
    from PIL import ImageFont, ImageDraw
except ImportError as e:
    print(f"Error: {e}")
    print("Install: pip install luma.oled pillow")
    sys.exit(1)

def test_display_config(device_type, rotation):
    """Test a specific display configuration"""
    print(f"\nTrying {device_type.__name__} with rotation={rotation}...")
    
    try:
        # Try SPI interface
        serial = spi(device=0, port=0, bus_speed_hz=8000000, transfer_size=4096)
        device = device_type(serial, rotate=rotation)
        
        # Try to draw something
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 10), "WAVESHARE", fill="white")
            draw.text((10, 25), "Display Test", fill="white")
            draw.text((10, 40), f"Rotation: {rotation}", fill="white")
        
        print(f"✓ SUCCESS with {device_type.__name__} rotation={rotation}")
        print(f"  Display size: {device.width}x{device.height}")
        return device
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return None

def run_simple_test():
    """Run simple display test with no GPIO"""
    print("="*60)
    print("Simple Display Test - No GPIO Buttons")
    print("="*60)
    
    # Try different configurations
    configs = [
        (sh1106, 0),   # SH1106 no rotation
        (sh1106, 2),   # SH1106 180° rotation
        (ssd1306, 0),  # SSD1306 no rotation
        (ssd1306, 2),  # SSD1306 180° rotation
    ]
    
    working_device = None
    
    for device_type, rotation in configs:
        working_device = test_display_config(device_type, rotation)
        if working_device:
            print(f"\n✓✓✓ Found working configuration! ✓✓✓")
            break
        time.sleep(0.5)
    
    if not working_device:
        print("\n✗ No working display configuration found!")
        print("\nTroubleshooting:")
        print("  1. Check SPI is enabled: ls /dev/spi*")
        print("  2. Check HAT connection")
        print("  3. Try: sudo raspi-config -> Interface Options -> SPI")
        return False
    
    # Run animation on working display
    print("\nRunning test animation...")
    try:
        font = ImageFont.load_default()
        
        for i in range(30):  # 3 seconds
            with canvas(working_device) as draw:
                draw.rectangle(working_device.bounding_box, outline="white", fill="black")
                
                # Title
                draw.text((5, 0), "WAVESHARE HAT", fill="white")
                
                # Current time
                now = datetime.now().strftime('%H:%M:%S')
                draw.text((5, 15), f"Time: {now}", fill="white")
                
                # Counter
                draw.text((5, 30), f"Count: {i}", fill="white")
                
                # Progress bar
                bar_width = int((i / 30) * 118)
                draw.rectangle((5, 50, 5 + bar_width, 55), fill="white")
            
            time.sleep(0.1)
        
        # Final message
        with canvas(working_device) as draw:
            draw.rectangle(working_device.bounding_box, outline="white", fill="black")
            draw.text((20, 25), "Display Works!", fill="white")
        
        time.sleep(2)
        
        # Clear display
        with canvas(working_device) as draw:
            draw.rectangle(working_device.bounding_box, outline="black", fill="black")
        
        print("\n✓ Display test complete!")
        return True
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
        return False
    except Exception as e:
        print(f"\n✗ Error during animation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nSimple Display Test")
    print("This tests ONLY the display - no GPIO buttons")
    print("Press Ctrl+C to stop\n")
    
    try:
        success = run_simple_test()
        if success:
            print("\n✓✓✓ All tests passed! ✓✓✓")
        else:
            print("\n✗ Test failed")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
