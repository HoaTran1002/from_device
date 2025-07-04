from machine import ADC, Timer, I2C, Pin
import gc
from machine import WDT
import machine
import utime
import time
import sys
import os
import ujson
from umqttsimple import MQTTClient
from wifi_utils import connect_wifi

# ===== DEVICE INFO =====
DEVICE_INFO_FILE = "device_info.txt"
FLAG_SKIP_UPDATE_FILE = "flag_skip_update.txt"
DEVICE_ADDRESS 		= 0x48
I2C_REG_VERSION 		= 0x00
I2C_REG_ID3 			= 0x01
I2C_REG_ID2 			= 0x02
I2C_REG_ID1 			= 0x03
I2C_REG_ID0 			= 0x04

SKIP_UPDATE_FLAG = False
client = None  # Khởi tạo biến toàn cục an toàn

i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)



def read_register_n(addr, reg):
    try:
        i2c.writeto(addr, bytes([reg]))
        utime.sleep_ms(10)
        data = i2c.readfrom(addr, 1)
        return data[0]
    except OSError as e:
        print("I2C communication error:", e)
        return None
def read_ID():
    version = read_register_n(DEVICE_ADDRESS, I2C_REG_VERSION)
    id3 = read_register_n(DEVICE_ADDRESS, I2C_REG_ID3)
    id2 = read_register_n(DEVICE_ADDRESS, I2C_REG_ID2)
    id1 = read_register_n(DEVICE_ADDRESS, I2C_REG_ID1)
    id0 = read_register_n(DEVICE_ADDRESS, I2C_REG_ID0)

    if None in [version, id0, id1, id2, id3]:
        print("[FATAL] I2C read failed: one or more ID registers returned None")
        return None  # hoặc raise Exception để fail rõ ràng

    imei = "{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}".format(
        id1, 19, id3, 0, version, 34, id2, id0
    )
    print("IMEI :", imei)
    return imei

def generate_default_device_info():
    imei = read_ID()
    if imei is None:
        raise Exception("Failed to read IMEI via I2C. Cannot proceed.")
    return {
        "IMEI": imei,
        "CURRENT_VERSION": "UNKNOWN",
        "CURRENT_MODEL": "RSX-511"
    }


def save_device_info(imei, current_version, current_model):
    with open(DEVICE_INFO_FILE, "w") as f:
        f.write(ujson.dumps({
            "IMEI": imei,
            "CURRENT_VERSION": current_version,
            "CURRENT_MODEL": current_model
        }))

def load_device_info():
    if DEVICE_INFO_FILE not in os.listdir():
        info = generate_default_device_info()
        save_device_info(info["IMEI"], info["CURRENT_VERSION"], info["CURRENT_MODEL"])
        return info
    with open(DEVICE_INFO_FILE, "r") as f:
        return ujson.loads(f.read())

info = load_device_info()
IMEI = info["IMEI"]
CURRENT_VERSION = info["CURRENT_VERSION"]
CURRENT_MODEL = info["CURRENT_MODEL"]

# ===== MQTT CONFIG =====
BROKER = "192.168.101.70"
USERNAME = "iot_device_1"
PASSWORD = "device_password_123"


def stop_main():
    if "main.py" in os.listdir():
        try:
            os.rename("main.py", "main.bak.py")
            print("[INFO] main.py renamed to main.bak.py to stop it from running.")
        except Exception as e:
            print("[WARN] Failed to rename main.py:", e)
    else:
        print("[INFO] No main.py found to stop.")

def restore_main():
    if "main.bak.py" in os.listdir() and "main.py" not in os.listdir():
        try:
            os.rename("main.bak.py", "main.py")
            print("[INFO] main.bak.py restored to main.py")
        except Exception as e:
            print("[WARN] Failed to restore main.py:", e)

def report_update_status_mqtt(status, log=""):
    global client
    topic = f"floor-inspector/device/{IMEI}/firmware/update/status/command"
    payload = ujson.dumps({
        "imei": IMEI,
        "status": status,
        "log": log,
    })
    print(f"[INFO] Reporting: {status} - {log}")
    client.publish(topic, payload)

def save_script(file_name, script_str):
    try:
        with open(file_name, "w") as f:
            f.write(script_str)
        return True
    except Exception as e:
        report_update_status_mqtt("FAILED", f"Save script failed: {e}")
        print("[ERROR] Save script failed:", e)
        return False


def run_script(file_name):
    try:
        if file_name not in os.listdir():
            return False, f"Script '{file_name}' not found on device"

        print(f"[INFO] Running script: {file_name}")

        with open(file_name) as f:
            script_code = f.read()

        exec_globals = {}
        exec(script_code, exec_globals)

        return True, f"{file_name} executed successfully"
    except Exception as e:
        print("[ERROR] Exception while running script:", e)
        return False, f"Exception while running {file_name}: {e}"


def handle_update_command(topic, msg):
    print("[INFO] Received update command ")
    global SKIP_UPDATE_FLAG
    try:
        data = ujson.loads(msg.decode())

        # ✅ Nếu không có cập nhật thì kết thúc
        if not data.get("updateAvailable", True):
            print("[INFO] No update available. Exiting script.")
            report_update_status_mqtt("COMPLETED", "No update required")
            with open(FLAG_SKIP_UPDATE_FILE, "w") as f:
                f.write(ujson.dumps({
                    "SKIP_UPDATE": True
                }))
            print("[FINISHED] No update available. Exiting script.")
            SKIP_UPDATE_FLAG = True
            return
            # client.disconnect()
            # machine.reset()
            # run_script("main.py")
            # return
            # sys.exit(0)
            # machine.reset()


        # Nếu có cập nhật thì tiếp tục như cũ
        script = data["script"]
        version = data["version"]
        file_name = f"{data['fileName']}.py"

        report_update_status_mqtt("IN_PROGRESS", "Script received")

        print(f"[INFO] Received script: {file_name}")
        print(f"[INFO] Script size: {len(script)} bytes")
        print("[INFO] Script content:")
        print(script)

        stop_main()
        if not save_script(file_name, script):
            report_update_status_mqtt("FAILED", "Script save failed")
            return

        report_update_status_mqtt("COMPLETED", "Saved script")
        # time.sleep(1)

        # success, log = run_script(file_name)
        # final_status = "COMPLETED" if success else "FAILED"

        # if success:
        save_device_info(IMEI, version, CURRENT_MODEL)
        with open(FLAG_SKIP_UPDATE_FILE, "w") as f:
            f.write(ujson.dumps({
                "SKIP_UPDATE": True
            }))
        print(f"[FINISHED] Updated version to {version}")

        # report_update_status_mqtt(final_status, log)
        # print(f"[INFO] Update status: {final_status} - {log}")
        # print("[FINISHED] Script finished.")
        # print(f"[FINISHED] Updated version to {version}")

        # time.sleep(1)

        # ✅ Đóng kết nối và thoát nếu hoàn tất update
        # client.disconnect()
        restore_main()
        # run_script("main.py")
        SKIP_UPDATE_FLAG = True
        # machine.reset()
        # sys.exit(0)
        # machine.reset()
        # exec(open("main.py").read())



    except Exception as e:
        print("[ERROR] Failed to handle update command:", e)
        report_update_status_mqtt("FAILED", f"Exception: {e}")
        SKIP_UPDATE_FLAG = True  # fallback để tránh kẹt

def create_mqtt_client():
    print("[INFO] Creating MQTT client...")
    client = MQTTClient(IMEI, BROKER, user=USERNAME, password=PASSWORD, port=1883)

    lwt_topic = f"floor-inspector/device/{IMEI}/connect/data"
    lwt_msg = ujson.dumps({"imei": IMEI, "status": "OFFLINE"})
    client.set_last_will(lwt_topic, lwt_msg)

    client.connect()
    print("[INFO] Connected to MQTT broker.")

    online_topic = f"floor-inspector/device/{IMEI}/connect/data"
    online_msg = ujson.dumps({"imei": IMEI, "status": "CONNECTED", "timestamp": time.time()})
    client.publish(online_topic, online_msg)
    print(f"[INFO] Published {online_msg} to {online_topic}")
    # Sub vào topic nhận script update
    update_topic = f"floor-inspector/device/{IMEI}/firmware/update/command"
    client.set_callback(handle_update_command)
    print("[INFO] MQTT client created. ===>>")
    client.subscribe(update_topic)
    print(f"[INFO] Subscribed to {update_topic}")

    return client

def request_check_update(client):
    print("[INFO] Requesting check_update.py...")
    check_topic = f"floor-inspector/device/{IMEI}/firmware/check/command"
    check_msg = ujson.dumps({
        "imei": IMEI,
        "currentVersion": CURRENT_VERSION,
        "currentModel": CURRENT_MODEL
    })
    print(f"[INFO] Requesting update check to {check_topic}")
    client.publish(check_topic, check_msg)

# ===== MAIN =====

def validate_config():
    required_vars = ['IMEI', 'BROKER', 'USERNAME', 'PASSWORD']
    missing = [var for var in required_vars if var not in globals() or not globals()[var]]
    if missing:
        print(f"[FATAL] Missing required config: {missing}")
        return False
    return True

def run_check_update():
    if not validate_config():
        return

    print(f"[INFO] Starting check_update at {time.time()}")
    print(f"[INFO] IMEI: {IMEI}, Broker: {BROKER}")

    try:
        print("[INFO] Connecting to Wi-Fi...")
        if not connect_wifi():
            print("[FATAL] Cannot proceed without Wi-Fi.")
            return
        print("[INFO] Wi-Fi connected.")

        global client
        client = create_mqtt_client()
        request_check_update(client)
        print("[INFO] check_update.py started.")

        # === Enhanced loop ===
        start_time = time.time()
        max_wait_time = 300  # 5 minutes timeout
        consecutive_errors = 0
        max_consecutive_errors = 10
        wdt = WDT(timeout=8000)

        while time.time() - start_time < max_wait_time:
            try:
                wdt.feed()
                client.check_msg()
                consecutive_errors = 0

                if int(time.time()) % 30 == 0:
                    gc.collect()
                    print(f"[DEBUG] Free memory: {gc.mem_free()} bytes")

                if SKIP_UPDATE_FLAG:
                    print("[INFO] Update process complete or skipped. Exiting loop.")
                    break

            except Exception as e:
                consecutive_errors += 1
                print(f"[WARN] MQTT check_msg failed ({consecutive_errors}/{max_consecutive_errors}): {e}")

                if consecutive_errors >= max_consecutive_errors:
                    print("[ERROR] Too many consecutive MQTT errors. Exiting loop.")
                    break

                time.sleep(min(consecutive_errors * 0.5, 5))  # Exponential backoff

            time.sleep(0.1)

        if time.time() - start_time >= max_wait_time:
            print("[WARN] Timeout reached. Exiting check_update.")

        try:
            client.disconnect()
        except:
            pass

    except Exception as ex:
        print("[FATAL] run_check_update crashed:", ex)
