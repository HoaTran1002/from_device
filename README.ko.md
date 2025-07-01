# MicroPython 펌웨어 업데이트 프로젝트

## 설명

이 프로젝트는 MQTT와 `mpremote`를 통해 MicroPython 장치의 펌웨어를 업데이트하는 것을 목표로 합니다.  
업데이트 과정에는 새로운 펌웨어 버전 확인, 업데이트 스크립트 다운로드, 메인 파일(`main.py`) 덮어쓰기, 장치 재시작이 포함됩니다.

---

## 구성 (Configuration)

배포하기 전에 다음 파일에서 중요한 구성 매개변수를 편집해야 합니다:

- **check_update.py**  
  - `BROKER` 변수를 귀하의 MQTT 브로커 주소로 변경하세요 (예: IP 또는 호스트명).

- **optimized_network_socket.py**  
  - `MQTT_BROKER` 변수를 해당 MQTT 브로커 주소로 변경하세요.

---

## 작업 흐름도

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
```

## 단계별 가이드: 펌웨어 업데이트 배포

### 전제 조건:
- 컴퓨터에 mpremote 도구가 설치되어 있어야 합니다.
- 터미널 명령을 실행하기 전에 다음 2개 파일에서 MQTT 주소를 수정하세요:
    - `check_update.py`: `BROKER` 변수를 업데이트하세요.
    - `optimized_network_socket.py`: `MQTT_BROKER` 변수를 업데이트하세요.
- 관리자 인터페이스에서: 장치 관리에서 IMEI를 등록해야 합니다.
- 관리자 인터페이스에서: 펌웨어 관리에서 장치에 적용할 새 펌웨어를 생성해야 합니다.
- 새 펌웨어를 생성할 때 정확한 업데이트 확인을 위해 `check_update` 스크립트가 있어야 합니다.

---

### 각 main.py 파일에 필요한 Python 코드

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

# 파일이 존재하지 않는 경우에만 생성
if FLAG_SKIP_UPDATE_FILE not in os.listdir():
    create_flag_skip_update_file()

# 스킵되지 않은 경우에만 check_update 실행
if not should_skip_update():
    run_check_update()

# 스킵하거나 확인 완료 후 → 측정 실행
print("[MAIN] Starting measurement socket...")
```

### 1단계: 장치의 모든 파일과 디렉토리 삭제
⚠️ 주의: 이 작업은 장치 메모리의 모든 데이터를 완전히 삭제합니다.

- 터미널에서 다음 명령을 사용하세요:
```
mpremote rm -rv :/
```

### 2단계: 필요한 파일을 장치에 복사
복사해야 할 파일들:
- check_update.py
- optimized_network_socket.py
- wifi_utils.py
- umqttsimple.py
- main.py

- 다음 명령을 사용하세요:
```
mpremote cp check_update.py optimized_network_socket.py wifi_utils.py umqttsimple.py main.py :/
```

### 3단계: 프로그램을 실행하기 위해 장치 재시작
```
mpremote reset
```

### 4단계 (선택사항): 업로드된 파일 확인
```
mpremote fs ls
```

