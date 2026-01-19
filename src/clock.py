"""
Old Train Station Clock Controller
Drives a vintage train station clock using a stepper motor driver.
"""

from machine import Pin, RTC
import time
import json
from collections import namedtuple

DEFAULT_TIME_SERVICE_URL = 'http://worldtimeapi.org/api/timezone/CET'

TimeValue = namedtuple("TimeValue", ("hours", "minutes", "seconds"))


class Clock:
    """
    Controller for an old train station clock using a stepper motor driver.
    
    The clock maintains persistent state of the displayed time and synchronizes
    with an online time service for accurate timekeeping.
    """
    
    def __init__(
        self, 
        nenabled_pin_number: int, 
        step_pin_number: int, 
        led_pin_number: int, 
        configuration_filename: str = "configuration.json", 
        display_time: str = None
    ) -> None:
        """
        Initialize the clock controller.
        
        Args:
            nenabled_pin_number: GPIO pin number for stepper driver enable (active low)
            step_pin_number: GPIO pin number for stepper driver step signal
            led_pin_number: GPIO pin number for status LED
            configuration_filename: Path to the JSON configuration file
            display_time: Optional initial display time in "HH:MM" or "HH:MM:SS" format
        """
        self.configuration_filename = configuration_filename
        self.current_display_minutes = 0
        self.time_service_url = DEFAULT_TIME_SERVICE_URL
        self._interactive_mode = False
        
        # Load existing configuration first
        self.load_configuration()
        
        # Override display time if explicitly provided
        if display_time is not None:
            display_timevalue = self.parse_time_string(display_time)
            self.current_display_minutes = self.calculate_display_minutes(display_timevalue)
            self.store_configuration()
        
        self.rtc = RTC()
        self.pin_step = Pin(step_pin_number, Pin.OUT)
        self.pin_nenabled = Pin(nenabled_pin_number, Pin.OUT)
        self.pin_nenabled.on()  # Disable stepper initially
        self.pin_led = Pin(led_pin_number, Pin.OUT)
        self.pin_led.on()  # LED off initially (active low)
    
    def sync_rtc_online(self) -> bool:
        """
        Synchronize the internal RTC with an online time service.
        
        Returns:
            True if synchronization was successful, False otherwise.
        """
        import requests
        self.pin_led.on()  # Turn LED off during sync
        
        try:
            print('Online time synchronization started...')
            response = requests.get(self.time_service_url, timeout=10)
            data = response.json()
            response.close()
            print('Received response:', str(data))
            
            # Parse the datetime string
            datetime_str = data["datetime"]
            # Format: "2024-01-15T14:30:45.123456+01:00"
            date_part, time_part = datetime_str.split("T")
            year, month, day = [int(x) for x in date_part.split("-")]
            
            # Handle timezone offset in time part
            if "+" in time_part:
                time_only, _ = time_part.split("+")
            elif time_part.count("-") > 0:
                # Negative timezone offset
                time_only = time_part.rsplit("-", 1)[0]
            else:
                time_only = time_part
            
            time_components = time_only.split(":")
            hour = int(time_components[0])
            minute = int(time_components[1])
            second_parts = time_components[2].split(".")
            second = int(second_parts[0])
            microsecond = int(second_parts[1]) if len(second_parts) > 1 else 0
            
            # day_of_week: 0 = Monday in MicroPython RTC
            day_of_week = data.get('day_of_week', 1) - 1
            if day_of_week < 0:
                day_of_week = 6  # Sunday becomes 6
            
            datetime_tuple = (year, month, day, day_of_week, hour, minute, second, microsecond)
            self.rtc.datetime(datetime_tuple)
            print('Time synchronization successful:', f"{hour:02d}:{minute:02d}:{second:02d}")
            self.pin_led.off()  # Turn LED on to indicate success
            return True
            
        except Exception as e:
            print('Time synchronization failed:', str(e))
            return False
    
    def store_configuration(self) -> bool:
        """
        Save the current configuration to persistent storage.
        
        Returns:
            True if save was successful, False otherwise.
        """
        try:
            configuration = {
                "display": self.current_display_minutes,
                "timezone_url": self.time_service_url
            }
            with open(self.configuration_filename, "w") as file:
                file.write(json.dumps(configuration))
                file.flush()  # Ensure data is written
            return True
        except Exception as e:
            print('Failed to save configuration:', str(e))
            return False
    
    def load_configuration(self) -> bool:
        """
        Load configuration from persistent storage.
        
        Returns:
            True if load was successful, False otherwise.
        """
        try:
            with open(self.configuration_filename, "r") as file:
                configuration = json.loads(file.read())
            
            print('Configuration loaded:', str(configuration))
            
            if "display" in configuration:
                self.current_display_minutes = int(configuration["display"])
            
            if "timezone_url" in configuration:
                self.time_service_url = configuration["timezone_url"]
            
            return True
            
        except OSError:
            print('Configuration file not found, using defaults.')
            self.current_display_minutes = 0
            self.time_service_url = DEFAULT_TIME_SERVICE_URL
            return False
        except (ValueError, KeyError) as e:
            print('Invalid configuration file, using defaults:', str(e))
            self.current_display_minutes = 0
            self.time_service_url = DEFAULT_TIME_SERVICE_URL
            return False
    
    def calculate_display_minutes(self, time_val: TimeValue) -> int:
        """
        Convert a TimeValue to display minutes (0-719 for 12-hour display).
        
        Args:
            time_val: TimeValue with hours, minutes, seconds
            
        Returns:
            Minutes from 12:00, in range 0-719
        """
        return ((time_val.hours * 60) + time_val.minutes) % (12 * 60)
    
    def parse_time_string(self, value: str) -> TimeValue:
        """
        Parse a time string into a TimeValue.
        
        Args:
            value: Time string in "HH:MM" or "HH:MM:SS" format
            
        Returns:
            TimeValue with parsed hours, minutes, seconds
            
        Raises:
            ValueError: If the time format is invalid
        """
        parts = value.split(":")
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError("Invalid time format. Use HH:MM or HH:MM:SS")
        
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = 0
        
        if len(parts) == 3:
            seconds = int(parts[2])
        
        if not (0 <= hours <= 23):
            raise ValueError("Hours must be between 0 and 23")
        if not (0 <= minutes <= 59):
            raise ValueError("Minutes must be between 0 and 59")
        if not (0 <= seconds <= 59):
            raise ValueError("Seconds must be between 0 and 59")
        
        return TimeValue(hours=hours, minutes=minutes, seconds=seconds)
    
    def display_minutes_to_time(self, display_minutes: int) -> TimeValue:
        """
        Convert display minutes to a TimeValue.
        
        Args:
            display_minutes: Minutes from 12:00 (0-719)
            
        Returns:
            TimeValue representing the display time
        """
        hours = (display_minutes // 60) % 12
        if hours == 0:
            hours = 12
        minutes = display_minutes % 60
        return TimeValue(hours=hours, minutes=minutes, seconds=0)
    
    def tick(self) -> None:
        """
        Advance the clock display by one minute.
        
        This sends the step signals to the stepper motor driver to move
        the clock hands forward by one minute.
        """
        self.pin_nenabled.off()  # Enable stepper driver
        time.sleep_ms(10)
        
        # Two steps for one minute (alternating polarity)
        for _ in range(2):
            self.pin_step.on()
            time.sleep_ms(25)
            self.pin_step.off()
            time.sleep_ms(250)
        
        self.pin_nenabled.on()  # Disable stepper driver
        self.current_display_minutes = (self.current_display_minutes + 1) % (12 * 60)
        self.store_configuration()
    
    def set_display_time(self, target_display_value: TimeValue, verbose: bool = True) -> None:
        """
        Set the clock display to a target time.
        
        Args:
            target_display_value: The target time to display
            verbose: Whether to print progress messages
        """
        target_display_minutes = self.calculate_display_minutes(target_display_value)
        
        while self.current_display_minutes != target_display_minutes:
            if verbose:
                current = self.display_minutes_to_time(self.current_display_minutes)
                target = self.display_minutes_to_time(target_display_minutes)
                print(f"{current.hours:02d}:{current.minutes:02d} -> {target.hours:02d}:{target.minutes:02d}")
            self.tick()
    
    def get_current_rtc_time(self) -> TimeValue:
        """
        Get the current time from the RTC.
        
        Returns:
            TimeValue with current RTC time
        """
        ctime = self.rtc.datetime()
        return TimeValue(hours=ctime[4], minutes=ctime[5], seconds=ctime[6])
    
    def print_help(self) -> None:
        """Print the interactive console help menu."""
        print("""
+-----------------------------------------------------------+
|          OLD TRAIN STATION CLOCK - CONSOLE MENU           |
+-----------------------------------------------------------+
|  Commands:                                                |
|    s, status     - Show current clock status              |
|    t HH:MM       - Set displayed time (e.g., t 14:30)     |
|    +N            - Advance clock by N minutes (e.g., +5)  |
|    -N            - Set back displayed time by N minutes   |
|    z URL         - Set timezone URL                       |
|    z list        - Show available timezone examples       |
|    sync          - Force RTC sync with online service     |
|    save          - Save current configuration             |
|    run           - Start automatic clock mode             |
|    h, help       - Show this help menu                    |
|    q, quit       - Exit interactive mode                  |
+-----------------------------------------------------------+
""")
    
    def print_timezone_list(self) -> None:
        """Print a list of example timezone URLs."""
        print("""
Available timezone examples (worldtimeapi.org):
  Europe:
    http://worldtimeapi.org/api/timezone/Europe/Warsaw
    http://worldtimeapi.org/api/timezone/Europe/London
    http://worldtimeapi.org/api/timezone/Europe/Paris
    http://worldtimeapi.org/api/timezone/Europe/Berlin
    http://worldtimeapi.org/api/timezone/CET
  Americas:
    http://worldtimeapi.org/api/timezone/America/New_York
    http://worldtimeapi.org/api/timezone/America/Los_Angeles
    http://worldtimeapi.org/api/timezone/America/Chicago
  Asia:
    http://worldtimeapi.org/api/timezone/Asia/Tokyo
    http://worldtimeapi.org/api/timezone/Asia/Shanghai

Full list: http://worldtimeapi.org/api/timezone
""")
    
    def interactive_console(self) -> None:
        """
        Run the interactive console for managing the clock via USB/serial.
        
        This provides a REPL-style interface for adjusting the displayed time,
        setting timezone, and monitoring clock status.
        """
        self._interactive_mode = True
        print("\n" + "=" * 60)
        print("  OLD TRAIN STATION CLOCK - Interactive Console")
        print("  Type 'help' for available commands")
        print("=" * 60 + "\n")
        
        # Show initial status
        self._show_status()
        
        while self._interactive_mode:
            try:
                cmd = input("\nclock> ").strip().lower()
                
                if not cmd:
                    continue
                
                if cmd in ('h', 'help'):
                    self.print_help()
                
                elif cmd in ('s', 'status'):
                    self._show_status()
                
                elif cmd.startswith('t '):
                    # Set time command
                    time_str = cmd[2:].strip()
                    try:
                        new_time = self.parse_time_string(time_str)
                        self.current_display_minutes = self.calculate_display_minutes(new_time)
                        self.store_configuration()
                        print(f"Display time set to {new_time.hours:02d}:{new_time.minutes:02d}")
                        self._show_status()
                    except ValueError as e:
                        print(f"Error: {e}")
                
                elif cmd.startswith('+'):
                    # Advance time
                    try:
                        minutes = int(cmd[1:])
                        if minutes > 0:
                            print(f"Advancing clock by {minutes} minute(s)...")
                            for i in range(minutes):
                                self.tick()
                                if (i + 1) % 10 == 0:
                                    print(f"  {i + 1}/{minutes} minutes done")
                            print("Done!")
                            self._show_status()
                        else:
                            print("Error: Please use a positive number")
                    except ValueError:
                        print("Error: Invalid number. Use +N (e.g., +5)")
                
                elif cmd.startswith('-'):
                    # Set back displayed time (not physical, just memory)
                    try:
                        minutes = int(cmd[1:])
                        if minutes > 0:
                            self.current_display_minutes = (self.current_display_minutes - minutes) % (12 * 60)
                            self.store_configuration()
                            print(f"Display time record adjusted back by {minutes} minute(s)")
                            self._show_status()
                        else:
                            print("Error: Please use a positive number")
                    except ValueError:
                        print("Error: Invalid number. Use -N (e.g., -5)")
                
                elif cmd == 'z list':
                    self.print_timezone_list()
                
                elif cmd.startswith('z '):
                    # Set timezone URL
                    url = cmd[2:].strip()
                    if url.startswith('http'):
                        self.time_service_url = url
                        self.store_configuration()
                        print(f"Timezone URL set to: {url}")
                        print("Use 'sync' to synchronize with the new timezone")
                    else:
                        print("Error: URL must start with http:// or https://")
                
                elif cmd == 'sync':
                    print("Synchronizing RTC with online service...")
                    if self.sync_rtc_online():
                        print("Synchronization successful!")
                    else:
                        print("Synchronization failed. Check connection and URL.")
                    self._show_status()
                
                elif cmd == 'save':
                    if self.store_configuration():
                        print("Configuration saved successfully!")
                    else:
                        print("Failed to save configuration.")
                
                elif cmd == 'run':
                    print("Starting automatic clock mode...")
                    print("Press Ctrl+C to return to interactive mode")
                    self._interactive_mode = False
                    self.start()
                
                elif cmd in ('q', 'quit', 'exit'):
                    print("Exiting interactive mode...")
                    self._interactive_mode = False
                    break
                
                else:
                    print(f"Unknown command: '{cmd}'. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'quit' to exit or 'run' to start clock.")
            except Exception as e:
                print(f"Error: {e}")
    
    def _show_status(self) -> None:
        """Display the current clock status."""
        display_time = self.display_minutes_to_time(self.current_display_minutes)
        rtc_time = self.get_current_rtc_time()
        
        print("")
        print("  Display Time: %02d:%02d" % (display_time.hours, display_time.minutes))
        print("  Actual Time:  %02d:%02d:%02d" % (rtc_time.hours, rtc_time.minutes, rtc_time.seconds))
        print("  Timezone:     " + self.time_service_url)
        
        # Calculate time difference
        display_total = self.current_display_minutes
        rtc_total = self.calculate_display_minutes(rtc_time)
        diff = (rtc_total - display_total) % (12 * 60)
        if diff > 6 * 60:  # More than 6 hours means we're "behind"
            diff = diff - 12 * 60
        
        if diff != 0:
            direction = "ahead" if diff > 0 else "behind"
            print("  Difference:   %d minute(s) %s" % (abs(diff), direction))
        print("")
    
    def start(self) -> None:
        """
        Start the main clock loop.
        
        This continuously synchronizes with the time service and updates
        the clock display to match the current time.
        """
        last_sync_hour = None
        
        print("Clock started. Press Ctrl+C to enter interactive mode.")
        
        try:
            while True:
                current_timevalue = self.get_current_rtc_time()
                print(f"Current RTC time: {current_timevalue.hours:02d}:{current_timevalue.minutes:02d}:{current_timevalue.seconds:02d}")
                
                # Sync with online service once per hour
                if current_timevalue.hours != last_sync_hour:
                    self.sync_rtc_online()
                    last_sync_hour = current_timevalue.hours
                
                # Update display to current time
                self.set_display_time(current_timevalue)
                
                # Sleep until the next minute
                ctime = self.rtc.datetime()
                delta = 60 - ctime[6]
                if delta > 0:
                    time.sleep(delta)
                    
        except KeyboardInterrupt:
            print("\n\nClock stopped. Entering interactive mode...")
            self.interactive_console()
