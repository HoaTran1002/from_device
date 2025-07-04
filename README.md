# MicroPython Firmware Update Project

## Mô tả

Dự án này hướng tới việc cập nhật firmware cho thiết bị MicroPython thông qua MQTT và `mpremote`.  
Quá trình cập nhật gồm việc kiểm tra phiên bản firmware mới, tải script cập nhật, ghi đè file chính (`main.py`), và khởi động lại thiết bị.

---

## Cấu hình (Configuration)

Trước khi triển khai, bạn cần chỉnh sửa các thông số cấu hình quan trọng trong các file sau:

- **check_update.py**  
  - Thay đổi biến `BROKER` thành địa chỉ MQTT Broker của bạn (ví dụ: IP hoặc hostname).

- **optimized_network_socket.py**  
  - Thay đổi biến `MQTT_BROKER` thành địa chỉ MQTT Broker tương ứng.

---

## Sơ đồ luồng hoạt động
![flow chart.png]
```mermaid
flowchart TD
    A[Start main.py] --> B[Call check_update.py]
    B --> C{update_available?}
    
    C -- No --> D[Return to main.py]
    D --> E[Continue main tasks]
    E --> F[End]

    C -- Yes --> G[Get update script]
    G --> H[Stop main]
    H --> I[Update main.py (overwrite)]
    I --> J[Restart main.py]
    J --> B2[Call check_update.py again]

    B2 --> C2{update_available?}
    C2 -- No --> D2[Exit check_update.py]
    D2 --> E2[Continue main tasks]
    E2 --> F2[End]

## Step-by-Step: Hướng dẫn triển khai cập nhật firmware

## Step-by-Step: Hướng dẫn triển khai cập nhật firmware

### Điều kiện tiên quyết:
- Đã cài đặt công cụ mpremote trên máy tính.
- Sửa địa chỉ MQTT trong 2 file sau trước khi thực thi các lệnh terminal:
    - `check_update.py`: cập nhật biến `BROKER`.
    - `optimized_network_socket.py`: cập nhật biến `MQTT_BROKER`.
- Tại giao diện admin: device management cần đăng ký IMEI.
- Tại giao diện admin: firmware management cần tạo 1 firmware mới để apply đến thiết bị.
- Khi tạo firmware mới cần có script `check_update` để đảm bảo việc check update chính xác.

---

### Mã Python cần có trong mỗi file main.py

```python
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


### Bước 1: Xóa toàn bộ file và thư mục trong thiết bị
⚠️ Lưu ý: Thao tác này sẽ xóa sạch toàn bộ dữ liệu trong bộ nhớ thiết bị.

- Dùng lệnh sau trong terminal:
    mpremote rm -rv :/

### Bước 2: Copy các file cần thiết vào thiết bị
Các file cần copy:
- check_update.py
- optimized_network_socket.py
- wifi_utils.py
- umqttsimple.py
- main.py

- Dùng lệnh sau:
    mpremote cp check_update.py wifi_utils.py umqttsimple.py optimized_network_socket.py main.py :/

### Bước 3: Khởi động lại thiết bị để chạy chương trình
- mpremote reset

### Bước 4 (tuỳ chọn): Kiểm tra lại các file đã nạp
- mpremote fs ls

