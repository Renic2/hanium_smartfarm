# -----------------------------------------------------------------------
# api.py
# FastAPI를 이용하여 프론트엔드와 통신하는 API 서버
# REST API와 WebSocket을 통해 실시간 데이터 조회 및 제어 기능 제공
# -----------------------------------------------------------------------

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading
import time
import json
import subprocess
import asyncio
from contextlib import asynccontextmanager

from fastapi.responses import HTMLResponse

from util import log
import config
from system_state import SystemState
from hardware_control import HardwareController
from camera_handler import CameraHandler

# --- Lifespan Manager (백그라운드 작업 관리) ---
# [수정됨] 기존 threading 방식 대신 FastAPI의 lifespan 이벤트를 사용하여 백그라운드 작업을 관리합니다.
# 이는 더 효율적이고 안정적인 방법입니다.
async def broadcast_loop():
    """ 일정 주기로 모든 WebSocket 클라이언트에게 상태를 브로드캐스트하는 비동기 루프. """
    while True:
        if system_state:
            state_data = system_state.get_full_state()
            await connection_manager.broadcast_state(state_data)
        await asyncio.sleep(2) # 비동기 sleep 사용

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시
    log.info("Starting background broadcast task...")
    # AP 모드가 아닐 때만 백그라운드 브로드캐스트 루프 시작
    if not app.state.ap_mode:
        task = asyncio.create_task(broadcast_loop())
    yield
    # 서버 종료 시
    if not app.state.ap_mode:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            log.info("Background broadcast task cancelled.")


class ConnectionManager:
    # 활성화된 WebSocket 연결을 관리하는 클래스
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
        # 모든 연결된 클라이언트에게 현재 상태를 브로드캐스트합니다.
        # datetime 객체는 JSON으로 바로 변환되지 않으므로 문자열로 변환
        if state.get('last_updated'):
            # get_full_state에서 이미 isoformat으로 변환하므로 이 부분은 필요 없을 수 있으나 안전을 위해 유지
            if not isinstance(state['last_updated'], str):
                 state['last_updated'] = state['last_updated'].isoformat()

        message = json.dumps(state)
        for connection in self.activate_connections:
            await connection.send_text(message)

# FastAPI 앱 생성 (lifespan 관리자 등록)
app = FastAPI(lifespan=lifespan)

# CORS 미들웨어 설정 (다른 출처의 요청 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용 (개발용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수 (main.py에서 주입받을 예정)
system_state: SystemState = None
hardware_controller: HardwareController = None
camera_handler = None
connection_manager = ConnectionManager()

# API 인증
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-KEY")):
    if x_api_key != config.API_SECRET_KEY:
        log.warning(f"Invalid API Key received: {x_api_key}")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

# REST API 엔드포인트
@app.get("/api/state", dependencies=[Depends(verify_api_key)])
async def get_current_state():
    return system_state.get_full_state()

@app.post("/api/control", dependencies=[Depends(verify_api_key)])
async def control_actuator(command: dict):
    device = command.get("device")
    value = command.get("value")
    if device and value is not None:
        log.info(f"[API] Manual control command received: {command}")
        hardware_controller.send_command(device, value)
        return {"status": "success", "command": command}
    raise HTTPException(status_code=400, detail="Invalid command format.")

@app.post("/api/setpoints", dependencies=[Depends(verify_api_key)])
async def set_new_targets(targets: dict):
    log.info(f"[API] Setpoints update received: {targets}")
    system_state.update_targets(targets)
    return {"status": "success", "updated_targets": system_state.get_full_state()['targets']}

@app.post("/api/camera/capture", dependencies=[Depends(verify_api_key)])
async def trigger_capture():
    if camera_handler:
        log.info("[API] Capture sequence initiated by user.")
        threading.Thread(target=camera_handler.capture_and_upload).start()
        return {"status": "success", "message": "Capture sequence initiated."}
    raise HTTPException(status_code=503, detail="Camera handler not available.")

# WebSocket 엔드포인트
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)

# [삭제됨] 기존 broadcast_loop 함수는 lifespan 관리자로 대체되었습니다.

# --- 서버 실행 함수 ---
def run_api_server(state_instance, hardware_instance, camera_instance, ap_mode=False):
    global system_state, hardware_controller, camera_handler
    system_state = state_instance
    hardware_controller = hardware_instance
    camera_handler = camera_instance
    
    # [수정됨] app.state를 통해 ap_mode 여부를 lifespan 관리자에게 전달
    app.state.ap_mode = ap_mode
    
    # [삭제됨] threading.Thread 호출은 lifespan으로 대체되었습니다.
    
    host_ip = "0.0.0.0"

    log.info(f"Starting API server in {'AP' if ap_mode else 'Normal'} mode on {host_ip}:8000")
    uvicorn.run(app, host=host_ip, port=8000)

# AP 모드 전용 엔드포인트
@app.get("/", response_class=HTMLResponse)
async def serve_setup_page():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Setup page not found.</h1>", status_code=404)

@app.get("/api/scan-wifi")
async def scan_wifi_networks():
    log.info("[AP_API] Scanning for Wi-Fi networks...")
    try:
        scan_output = subprocess.check_output(
            ['sudo', 'iwlist', 'wlan0', 'scan']
        ).decode('utf-8')
        
        ssids = set()
        for line in scan_output.split('\n'):
            if "ESSID:" in line:
                ssid = line.split('"')[1]
                if ssid:
                    ssids.add(ssid)

        log.info(f"Found networks: {list(ssids)}")
        return {"networks": sorted(list(ssids))}
    
    except Exception as e:
        log.error(f"Wi-Fi scan failed: {e}")
        return {"error": "Failed to scan networks."}
    
@app.post("/api/save-wifi")
async def save_wifi_credentials(credentials: dict):
    ssid = credentials.get("ssid")
    password = credentials.get("password")

    if not ssid or not password:
        raise HTTPException(status_code=400, detail="SSID and password are required.")

    log.info(f"[AP_API] Received new Wi-Fi credentials for SSID: {ssid}")
    
    network_config = f'''
        network={{
        ssid="{ssid}"
        psk="{password}"
        }}
    '''

    try:
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as f:
            f.write(network_config)
        
        log.info("Wi-Fi credentials saved. Rebooting device in 5 seconds...")
        
        def reboot_device():
            time.sleep(5)
            subprocess.run(["sudo", "reboot"])

        threading.Thread(target=reboot_device).start()
        
        return {"status": "success", "message": "Credentials saved. Device will reboot."}
    except Exception as e:
        log.error(f"Failed to save Wi-Fi credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to save credentials.")

if __name__ == "__main__":
    import sys
    if "--ap-mode" in sys.argv:
        run_api_server(None, None, None, ap_mode=True)