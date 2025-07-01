import machine
import network
import utime
from machine import Pin, WDT

led = Pin(10, Pin.OUT)
wdt = WDT(timeout=8000)

WIFI_NETWORKS = [
    {'ssid': 'JH PARTNERS L1', 'password': 'haveaniceday'},
    {'ssid': 'Metainnotech-03', 'password': '55054026'}
]

WIFI_TIMEOUT = 30
CONNECT_RETRY_DELAY = 500
MAX_WIFI_RETRIES = 3

wlan = None
current_connected_ssid = None

def log_info(msg):
    print("[INFO]", msg)

def log_error(msg):
    print("[ERROR]", msg)

def scan_and_connect_wifi():
    global wlan, current_connected_ssid
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    utime.sleep_ms(1000)

    for retry in range(MAX_WIFI_RETRIES):
        log_info(f"WiFi attempt {retry + 1}/{MAX_WIFI_RETRIES}")
        try:
            networks = wlan.scan()
            available = [net[0].decode() for net in networks]
            for wifi in WIFI_NETWORKS:
                ssid, password = wifi['ssid'], wifi['password']
                if ssid in available:
                    log_info(f"Connecting to {ssid}...")
                    wlan.connect(ssid, password)
                    start = utime.ticks_ms()
                    while not wlan.isconnected():
                        if utime.ticks_diff(utime.ticks_ms(), start) > WIFI_TIMEOUT * 1000:
                            log_error("Timeout")
                            break
                        utime.sleep_ms(100)
                        wdt.feed()
                    if wlan.isconnected():
                        current_connected_ssid = ssid
                        log_info(f"Connected: {wlan.ifconfig()}")
                        return True
        except Exception as e:
            log_error(f"WiFi error: {e}")
        utime.sleep_ms(CONNECT_RETRY_DELAY)
    return False

def connect_wifi():
    return scan_and_connect_wifi()
