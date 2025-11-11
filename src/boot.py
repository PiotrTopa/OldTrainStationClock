# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

from clock import Clock

WIFI_SSID = 'YourWifiSSID'
WIFI_PASS = 'MySecretPassword'

def wifi_connect():
    import machine, network
    wlan = network.WLAN()
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            machine.idle()
    print('network config:', wlan.ipconfig('addr4'))

wifi_connect()
clock = Clock(6, 7, 8)
clock.start()