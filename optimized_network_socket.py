import network
import utime
import ntptime
import gc
from machine import Pin, WDT
# Global variables
wlan = None
wdt = None  # Watchdog timer passed from main

from umqttsimple import MQTTClient
import ubinascii # For MQTT Client ID
import ujson # For MQTT payload serialization

# MQTT Configuration
MQTT_BROKER = "192.168.101.67"  # Replace with your MQTT broker address
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "floor-inspector/device"
MQTT_TOPIC_SUFFIX = "data"
MQTT_USER = "iot_device_1" # Optional: MQTT username
MQTT_PASSWORD = "device_password_123" # Optional: MQTT password
MQTT_KEEP_ALIVE = 60

# Global MQTT variables
mqtt_client = None
MQTT_CLIENT_ID = None # Will be set dynamically using IMEI
MQTT_TOPIC = None # Will be set dynamically using IMEI

# WiFi credentials - you should load these from a config file
WIFI_SSID = "JH PARTNERS L1"
WIFI_PASSWORD = "haveaniceday"

def log_info(message):
    """Simple logging function"""
    timestamp = get_current_time()
    print(f"[{timestamp}] INFO: {message}")

def log_error(message):
    """Simple error logging function"""
    timestamp = get_current_time()
    print(f"[{timestamp}] ERROR: {message}")

def get_current_time():
    """Get current time as Unix timestamp in milliseconds"""
    try:
        # utime.time() returns seconds since epoch (Jan 1, 2000, or Jan 1, 1970 if RTC is set)
        # For MicroPython, epoch is often 2000-01-01. If NTP is synced, it should be Unix epoch.
        # We need to ensure NTP is synced for this to be a true Unix timestamp.
        # Assuming NTP has been synced and utime.time() gives seconds since Unix epoch.
        return utime.time() * 1000
    except Exception as e:
        log_error(f"Error getting current time: {e}")
        # Fallback to a clearly identifiable non-valid timestamp if error occurs
        # or if time is not set (e.g. utime.time() might return seconds from device boot)
        # A large negative number or 0 could be options, but returning a fixed past date
        # might be confusing. Let's return 0, indicating epoch or unset time.
        return 0

def get_wifi_rssi():
    """Get WiFi signal strength (RSSI) in dBm"""
    global wlan
    
    try:
        if wlan and wlan.active() and wlan.isconnected():
            return wlan.status('rssi')
        else:
            return -100  # Return very weak signal if not connected
    except Exception as e:
        log_error(f"Failed to get WiFi RSSI: {e}")
        return -100

def connect_wifi():
    """Connect to WiFi network with watchdog feeding and proper timeout handling"""
    global wlan
    
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        # Wait for WiFi to activate
        utime.sleep_ms(1000)
        
        if wlan.isconnected():
            log_info(f"Already connected to WiFi: {wlan.ifconfig()[0]}")
            return True
            
        log_info(f"Connecting to WiFi: {WIFI_SSID}")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        # Wait for connection with timeout and watchdog feeding
        timeout = 20  # 20 seconds
        start_time = utime.ticks_ms()
        attempts = 0
        
        while not wlan.isconnected():
            elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
            if elapsed > timeout * 1000:
                log_error("WiFi connection timeout")
                return False
                
            attempts += 1
            if attempts % 10 == 0:  # Log every second
                log_info(f"Connecting to {WIFI_SSID}... ({elapsed//1000}s)")
            
            # Feed watchdog to prevent reset during connection
            if wdt:
                try:
                    wdt.feed()
                except:
                    pass  # Ignore if WDT feed fails
                
            utime.sleep_ms(100)  # Shorter sleep interval
            
        ip_info = wlan.ifconfig()
        log_info(f"WiFi connected! IP: {ip_info[0]}")
        log_info(f"RSSI: {wlan.status('rssi')}dBm")
        
        return True
        
    except Exception as e:
        log_error(f"WiFi connection failed: {e}")
        return False

def sync_time():
    """Synchronize time with NTP server"""
    try:
        log_info("Syncing time with NTP...")
        ntptime.settime()
        log_info("Time synchronized successfully")
        return True
    except Exception as e:
        log_error(f"NTP sync failed: {e}")
        return False

def get_connected_ssid():
    """Get the SSID of connected WiFi network"""
    global wlan
    if wlan and wlan.isconnected():
        try:
            return wlan.config('essid')
        except:
            return WIFI_SSID  # Fallback to configured SSID
    return "Not connected"

def connect_mqtt_broker():
    """Connects to the MQTT broker."""
    global mqtt_client, MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_KEEP_ALIVE
    if not MQTT_CLIENT_ID:
        log_error("MQTT_CLIENT_ID is not set. Cannot connect to MQTT broker.")
        return False
    try:
        log_info(f"Attempting to connect to MQTT broker: {MQTT_BROKER} with Client ID: {MQTT_CLIENT_ID}")
        mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD, keepalive=MQTT_KEEP_ALIVE)
        mqtt_client.connect()
        log_info(f"Successfully connected to MQTT broker: {MQTT_BROKER}")
        return True
    except Exception as e:
        log_error(f"MQTT connection failed: {e}")
        mqtt_client = None
        return False

def publish_to_mqtt(topic, payload):
    """Publishes a message to the specified MQTT topic."""
    global mqtt_client
    try:
        if not mqtt_client:
            log_error("MQTT client not connected. Attempting to reconnect...")
            if not connect_mqtt_broker():
                log_error("MQTT reconnection failed. Data not sent.")
                return False
            log_info("MQTT reconnected. Proceeding to send data.")
        
        mqtt_client.publish(topic, ujson.dumps(payload).encode('utf-8'))
        log_info(f"Successfully published message to topic: {topic.decode() if isinstance(topic, bytes) else topic}")
        return True
    except Exception as e:
        log_error(f"Failed to publish message to MQTT: {e}")
        # Consider if client should be set to None here to trigger reconnect on next attempt
        # mqtt_client = None 
        return False

def disconnect_mqtt():
    """Disconnects from the MQTT broker."""
    global mqtt_client
    if mqtt_client:
        try:
            mqtt_client.disconnect()
            log_info("Disconnected from MQTT broker.")
        except Exception as e:
            log_error(f"Error disconnecting MQTT client: {e}")
        finally:
            mqtt_client = None


# The function send_data_to_server_soket has been removed as data transmission is now handled by MQTT directly in optimized_main.py.


def calculate_average(data_list):
    """Calculate average of a list of numbers"""
    if len(data_list) == 0:
        return 0
    return sum(data_list) / len(data_list)

def log_average_values(sensor_values_n, sensor_values_x, sensor_values_y, sensor_values_z, sensor_values_t, sensor_values_h):
    """Log average sensor values"""
    avg_noise = calculate_average(sensor_values_n)
    avg_x = calculate_average(sensor_values_x)
    avg_y = calculate_average(sensor_values_y)
    avg_z = calculate_average(sensor_values_z)
    avg_temp = calculate_average(sensor_values_t)
    avg_humidity = calculate_average(sensor_values_h)
    
    log_info(f"[T: {avg_temp:.2f}Â°C | H: {avg_humidity:.2f}%]")
    log_info(f"[Mic: {avg_noise:.2f} | Rssi: {wlan.status('rssi') if wlan else 0}dBm]")
    log_info(f"[X: {avg_x:.2f} | Y: {avg_y:.2f} | Z: {avg_z:.2f}]")

def initialize_network_and_mqtt(imei_value):
    """Initializes network, sets up MQTT client ID and topic, and connects to MQTT."""
    global MQTT_CLIENT_ID, MQTT_TOPIC, mqtt_client
    log_info("Initializing network and MQTT...")

    # Connect to WiFi
    if not connect_wifi():
        log_error("WiFi connection failed during initialization.")
        return False

    # Sync time
    sync_time()

    # Setup MQTT client ID and Topic using the provided IMEI
    if not imei_value:
        log_error("IMEI value is not provided. Cannot initialize MQTT client.")
        return False
    
    MQTT_CLIENT_ID = ubinascii.hexlify(imei_value.encode()) # Use IMEI for MQTT Client ID
    MQTT_TOPIC = f"{MQTT_TOPIC_PREFIX}/{imei_value}/{MQTT_TOPIC_SUFFIX}".encode('utf-8')
    log_info(f"MQTT Client ID set to: {MQTT_CLIENT_ID}")
    log_info(f"MQTT Topic set to: {MQTT_TOPIC.decode()}")

    # Connect to MQTT broker
    if not connect_mqtt_broker():
        log_error("Failed to connect to MQTT broker during initialization.")
        # Depending on requirements, might allow operation without MQTT or fail hard
        return False 

    log_info("Network and MQTT initialization complete.")
    return True


def cleanup():
    """Clean up network resources, primarily WiFi."""
    global wlan
    log_info("Cleaning up network resources...")
    
    # Disconnect WiFi
    if wlan and wlan.isconnected():
        try:
            log_info("Disconnecting WiFi...")
            wlan.disconnect()
            wlan.active(False)
            log_info("WiFi disconnected.")
        except Exception as e:
            log_error(f"Error disconnecting WiFi: {e}")
    else:
        log_info("WiFi already disconnected or not initialized.")
    wlan = None # Ensure wlan is reset
        
    gc.collect()
    log_info("Network cleanup complete.")

# Enhanced error recovery
def recover_connection():
    """Attempt to recover from connection errors by reconnecting WiFi and MQTT."""
    log_info("Attempting MQTT connection recovery...")

    # Disconnect existing MQTT client first
    disconnect_mqtt() # This handles setting mqtt_client to None
    
    gc.collect()
    utime.sleep_ms(2000)

    # Reconnect WiFi if needed
    if not (wlan and wlan.isconnected()):
        log_info("WiFi not connected. Attempting to reconnect WiFi...")
        if not connect_wifi():
            log_error("WiFi reconnection failed during recovery process.")
            return False
        log_info("WiFi reconnected successfully.")
    
    # Try to re-establish MQTT connection
    log_info("Attempting to reconnect to MQTT broker after WiFi check...")
    if connect_mqtt_broker():
        log_info("MQTT connection recovered successfully.")
        return True
    else:
        log_error("Failed to recover MQTT connection.")
        return False




# Memory usage monitoring
def log_memory_usage():
    """Log current memory usage"""
    free_mem = gc.mem_free()
    log_info(f"Free memory: {free_mem} bytes")
    return free_mem

# Alias for backward compatibility
init_network_and_mqtt = initialize_network_and_mqtt