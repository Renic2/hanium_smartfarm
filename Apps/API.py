# -----------------------------------------------------------------------
# api.py
# FastAPI를 이용하여 프론트엔드와 통신하는 API 서버
# REST API와 WebSocket을 통해 실시간 데이터 조회 및 제어 기능 제공
# -----------------------------------------------------------------------

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
import threading
import time
import json
import subprocess
import asyncio
from contextlib import asynccontextmanager

# [수정] 변경된 모듈 이름으로 임포트
from Utility import log
import Config
from _System_ import SystemState
from Arduino_control import HardwareController
from CLI_control import CameraHandler # Camera_handler 모듈명 가정

# --- 백그라운드 작업 및 WebSocket 관리 ---

async def broadcast_loop():
    """일정 주기로 모든 WebSocket 클라이언트에게 상태를 브로드캐스트합니다."""
    while True:
        if system_state:
            # SystemState의 public 메서드 사용
            state_data = system_state.get_all_data()
            await connection_manager.broadcast_state(state_data)
        await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 시 백그라운드 작업을 관리합니다."""
    log.info("Starting background broadcast task...")
    if not app.state.ap_mode:
        task = asyncio.create_task(broadcast_loop())
    yield
    if not app.state.ap_mode:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            log.info("Background broadcast task cancelled.")

class ConnectionManager:
    """활성화된 WebSocket 연결을 관리합니다."""
    def __init__(self):
        self.activate_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.activate_connections.append(websocket)
        log.info("WebSocket client connected.")

    def disconnect(self, websocket: WebSocket):
        self.activate_connections.remove(websocket)
        log.info("WebSocket client disconnected.")

    async def broadcast_state(self, state: dict):
        message = json.dumps(state, default=str)
        for connection in self.activate_connections:
            await connection.send_text(message)

# --- FastAPI 앱 설정 ---
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 전역 인스턴스 ---
system_state: SystemState = None
hardware_controller: HardwareController = None
camera_handler: CameraHandler = None
connection_manager = ConnectionManager()

# --- API 인증 ---
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-KEY")):
    """요청 헤더의 API 키를 검증합니다."""
    # [수정] 모듈 이름 변경
    if x_api_key != Config.API_SECRET_KEY:
        log.warning(f"Invalid API Key received: {x_api_key}")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

# --- 일반 모드 API 엔드포인트 ---
@app.get("/api/state", dependencies=[Depends(verify_api_key)])
async def get_current_state():
    """현재 시스템의 전체 상태를 반환합니다."""
    return system_state.get_all_data()

@app.post("/api/control", dependencies=[Depends(verify_api_key)])
async def control_actuator(command: dict):
    """수동으로 액추에이터를 제어하는 명령을 수신합니다."""
    device = command.get("device")
    value = command.get("value")
    if device and value is not None:
        log.info(f"[API] Manual control command received: {command}")
        hardware_controller.send_command(device, value)
        return {"status": "success", "command": command}
    raise HTTPException(status_code=400, detail="Invalid command format.")

@app.post("/api/setpoints", dependencies=[Depends(verify_api_key)])
async def set_new_targets(targets: dict):
    """자동 제어를 위한 새로운 목표값을 설정합니다."""
    log.info(f"[API] Setpoints update received: {targets}")
    # [수정] update_values 메서드를 사용하여 TARGET 값만 업데이트
    updated_data = system_state.update_values({"TARGET": targets})
    return {"status": "success", "updated_targets": updated_data['TARGET']}

@app.post("/api/mode", dependencies=[Depends(verify_api_key)])
async def set_system_mode(mode_data: dict):
    """'AUTO' 또는 'MANUAL' 모드를 설정합니다."""
    mode = mode_data.get("mode")
    if mode and mode.upper() in ["AUTO", "MANUAL"]:
        log.info(f"[API] Mode change received: {mode}")
        # SystemState의 update_values를 재활용하여 모드를 변경합니다.
        system_state.update_values({"MODE": mode.upper()})
        return {"status": "success", "updated_mode": system_state.get_all_data()['MODE']}
    raise HTTPException(status_code=400, detail="Invalid mode value. Must be 'AUTO' or 'MANUAL'.")

@app.post("/api/camera/capture", dependencies=[Depends(verify_api_key)])
async def trigger_capture():
    """사용자 요청에 의해 카메라 촬영 시퀀스를 시작합니다."""
    if camera_handler:
        log.info("[API] Capture sequence initiated by user.")
        threading.Thread(target=camera_handler.capture_and_upload).start()
        return {"status": "success", "message": "Capture sequence initiated."}
    raise HTTPException(status_code=503, detail="Camera handler not available.")

# --- WebSocket 엔드포인트 ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """실시간 상태 브로드캐스트를 위한 WebSocket 연결을 처리합니다."""
    await connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


# --- AP 모드 API 엔드포인트 ---
@app.get("/", response_class=HTMLResponse)
async def serve_setup_page():
    """초기 설정을 위한 웹페이지(index.html)를 제공합니다."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Setup page not found.</h1>", status_code=404)

@app.get("/api/get-values")
async def get_current_values():
    """프론트엔드로 현재 설정값(value.json)을 보냅니다."""
    # AP 모드에서는 전역 system_state가 없으므로, 필요할 때마다 인스턴스 생성
    state_manager = SystemState()
    return state_manager.get_all_data()

@app.post("/api/save-values")
async def save_new_values(update_data: dict):
    """프론트에서 받은 값으로 기존 설정을 '안전하게' 업데이트합니다."""
    state_manager = SystemState()
    updated_values = state_manager.update_values(update_data)
    return {"status": "success", "message": "Values updated successfully.", "data": updated_values}


@app.get("/api/scan-wifi")
async def scan_wifi_networks():
    """주변의 Wi-Fi 네트워크를 스캔하여 목록을 반환합니다."""
    # (이하 Wi-Fi 관련 코드는 변경 없음)
    log.info("[AP_API] Scanning for Wi-Fi networks...")
    try:
        scan_output = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan']).decode('utf-8')
        ssids = sorted(list(set(line.split('"')[1] for line in scan_output.split('\n') if "ESSID:" in line and line.split('"')[1])))
        log.info(f"Found networks: {ssids}")
        return {"networks": ssids}
    except Exception as e:
        log.error(f"Wi-Fi scan failed: {e}")
        return {"error": "Failed to scan networks."}

@app.post("/api/save-wifi")
async def save_wifi_credentials(credentials: dict):
    """Wi-Fi 접속 정보를 받아 저장하고 장치를 재부팅합니다."""
    ssid = credentials.get("ssid")
    password = credentials.get("password")
    if not ssid or not password:
        raise HTTPException(status_code=400, detail="SSID and password are required.")
    log.info(f"[AP_API] Received new Wi-Fi credentials for SSID: {ssid}")
    try:
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as f:
            f.write(f'\nnetwork={{\n\tssid="{ssid}"\n\tpsk="{password}"\n}}\n')
        log.info("Wi-Fi credentials saved. Rebooting device in 5 seconds...")
        threading.Thread(target=lambda: (time.sleep(5), subprocess.run(["sudo", "reboot"]))).start()
        return {"status": "success", "message": "Credentials saved. Device will reboot."}
    except Exception as e:
        log.error(f"Failed to save Wi-Fi credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to save credentials.")

# --- 서버 실행 ---
def run_api_server(state_instance, hardware_instance, camera_instance, ap_mode=False):
    """API 서버를 실행합니다."""
    global system_state, hardware_controller, camera_handler
    system_state = state_instance
    hardware_controller = hardware_instance
    camera_handler = camera_instance
    app.state.ap_mode = ap_mode
    host_ip = "0.0.0.0"
    log.info(f"Starting API server in {'AP' if ap_mode else 'Normal'} mode on {host_ip}:8000")
    uvicorn.run(app, host=host_ip, port=8000)

if __name__ == "__main__":
    import sys
    is_ap_mode = "--ap-mode" in sys.argv
    run_api_server(None, None, None, ap_mode=is_ap_mode)