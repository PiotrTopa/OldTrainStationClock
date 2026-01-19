# This file is executed on every boot (including wake-boot from deepsleep)
# Keep this file minimal - main code should be in main.py
# esp.osdebug(None)
# import webrepl
# webrepl.start()

import json

# Default WiFi credentials (override in configuration.json)
DEFAULT_WIFI_SSID = 'your_wifi_ssid'
DEFAULT_WIFI_PASS = 'your_wifi_password'

# Configuration file path
CONFIG_FILE = 'configuration.json'


def load_wifi_config():
    """Load WiFi credentials from configuration file."""
    try:
        with open(CONFIG_FILE, "r") as file:
            config = json.loads(file.read())
        ssid = config.get('wifi_ssid', DEFAULT_WIFI_SSID)
        password = config.get('wifi_password', DEFAULT_WIFI_PASS)
        return ssid, password
    except Exception as e:
        print("Failed to load WiFi config:", str(e))
        return DEFAULT_WIFI_SSID, DEFAULT_WIFI_PASS


def wifi_connect():
    """Connect to WiFi network using credentials from configuration."""
    import machine
    import network
    
    ssid, password = load_wifi_config()
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print('Connecting to WiFi: ' + ssid + '...')
        wlan.connect(ssid, password)
        
        # Wait for connection with timeout
        import time
        timeout = 30
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
        
        if wlan.isconnected():
            print('WiFi connected!')
            print('Network config:', wlan.ifconfig())
        else:
            print('WiFi connection failed. Clock will run in offline mode.')
    else:
        print('Already connected to WiFi')
        print('Network config:', wlan.ifconfig())


print("\n==================================================")
print("  OLD TRAIN STATION CLOCK")
print("  Starting up...")
print("==================================================\n")

try:
    wifi_connect()
except Exception as e:
    print("WiFi error:", str(e))