# import ujson
# import os
# import time

# FLAG_SKIP_UPDATE_FILE = "flag_skip_update.txt"

# def create_flag_skip_update_file():
#     with open(FLAG_SKIP_UPDATE_FILE, "w") as f:
#         f.write(ujson.dumps({
#             "SKIP_UPDATE": False
#         }))
# create_flag_skip_update_file()
# def run_check_update():
#     try:
#         print("[INFO] Running check_update.py...")
#         with open("check_update.py") as f:
#             exec(f.read(), {})
#     except Exception as e:
#         print("[ERROR] Failed to run check_update.py:", e)

# def should_skip_update():
#     try:
#         if FLAG_SKIP_UPDATE_FILE not in os.listdir():
#             print("[INFO] flag_skip_update.txt not found → MUST check update")
#             return False
#         with open(FLAG_SKIP_UPDATE_FILE) as f:
#             time.sleep(1)
#             data = ujson.loads(f.read())
#             return data.get("SKIP_UPDATE", False) is True
#     except Exception as e:
#         print("[WARN] Failed to read SKIP_UPDATE flag:", e)
#         return False

# if not should_skip_update():
#     run_check_update()

import ujson
import os
from check_update import run_check_update

FLAG_SKIP_UPDATE_FILE = "flag_skip_update.txt"

def create_flag_skip_update_file():
    with open(FLAG_SKIP_UPDATE_FILE, "w") as f:
        f.write(ujson.dumps({"SKIP_UPDATE": False}))

def should_skip_update():
    try:
        if FLAG_SKIP_UPDATE_FILE not in os.listdir():
            print("[INFO] flag_skip_update.txt not found → MUST check update")
            return False
        with open(FLAG_SKIP_UPDATE_FILE) as f:
            data = ujson.loads(f.read())
            return data.get("SKIP_UPDATE", False) is True
    except Exception as e:
        print("[WARN] Failed to read SKIP_UPDATE flag:", e)
        return False

# Chỉ tạo file nếu chưa tồn tại
if FLAG_SKIP_UPDATE_FILE not in os.listdir():
    create_flag_skip_update_file()

# Chỉ chạy check_update nếu chưa bị skip
if not should_skip_update():
    run_check_update()

# Sau khi skip hoặc check xong → chạy đo lường
print("[MAIN] Starting measurement socket...")
