# Main application file - runs after boot.py
# This file starts the clock controller

from clock import Clock

print("\nInitializing clock...")

try:
    # Initialize clock with GPIO pins:
    # Pin 6: NOT_ENABLED (stepper driver enable, active low)
    # Pin 7: STEP (stepper driver step signal)
    # Pin 8: LED (status indicator)
    clock = Clock(6, 7, 8)
    
    print("Clock initialized successfully!")
    print("Display minutes:", clock.current_display_minutes)
    print("Timezone URL:", clock.time_service_url)
    print("")
    print("Starting clock...")
    print("Press Ctrl+C to enter interactive mode")
    print("")
    
    # Start the clock (will enter interactive mode on Ctrl+C)
    clock.start()
    
except Exception as e:
    print("ERROR: Clock initialization failed!")
    print("Error:", str(e))
    import sys
    sys.print_exception(e)
