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

from util import log
import config
from system_state import SystemState
from hardware_control import HardwareController
from camera_handler import CameraHandler

class ConnectionManager:
    # 활성화된 WebSocket 연결을 관리하는 클래스
    def __init__(self):
        self.activate_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.activate_connections.append(websocket)
        log.info("WebSocket client connected.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        log.info("WebSocket client disconnected.")

    async def broadcast_state(self, state: dict):
        # 모든 연결된 클라이언트에게 현재 상태를 브로드캐스트합니다.
        # datetime 객체는 JSON으로 바로 변환되지 않으므로 문자열로 변환
        if state.get('last_updated'):
             state['last_updated'] = state['last_updated'].isoformat()
             
        message = json.dumps(state)
        for connection in self.active_connections:
            await connection.send_text(message)

# FastAPI 앱 생성
app = FastAPI()

# CORS 미들웨어 설정 (다른 출처의 요청 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용 (개발용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수 (main.py에서 주입받을 예정)
# 이 변수들은 main.py에서 실제 객체로 초기화됩니다.
system_state: SystemState = None
hardware_controller: HardwareController = None
camera_handler = None
connection_manager = ConnectionManager()

# API 인증
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-KEY")):
    # API 키를 검증하는 의존성 함수.
    if x_api_key != config.API_SECRET_KEY:
        log.warning(f"Invalid API Key received: {x_api_key}")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

# REST API 엔드포인트
@app.get("/api/state", dependencies=[Depends(verify_api_key)])
async def get_current_state():
    # 시스템의 전체 현재 상태를 반환합니다.
    return system_state.get_full_state()

@app.post("/api/control", dependencies=[Depends(verify_api_key)])
async def control_actuator(command: dict):
    # 수동으로 장치를 제어합니다. 예: {"device": "FAN", "value": 255}
    device = command.get("device")
    value = command.get("value")
    if device and value is not None:
        log.info(f"[API] Manual control command received: {command}")
        hardware_controller.send_command(device, value)
        return {"status": "success", "command": command}
    raise HTTPException(status_code=400, detail="Invalid command format.")

@app.post("/api/setpoints", dependencies=[Depends(verify_api_key)])
async def set_new_targets(targets: dict):
    # 새로운 자동 제어 목표값을 설정합니다. 예: {"TARGET_TEMP": 26.5}
    log.info(f"[API] Setpoints update received: {targets}")
    system_state.update_targets(targets)
    return {"status": "success", "updated_targets": system_state.get_full_state()['targets']}

@app.post("/api/camera/capture", dependencies=[Depends(verify_api_key)])
async def trigger_capture():
    # 사진 촬영 및 업로드 시퀀스를 시작시킵니다.
    if camera_handler:
        log.info("[API] Capture sequence initiated by user.")
        # 촬영은 시간이 걸릴 수 있으므로 백그라운드 스레드에서 실행
        threading.Thread(target=camera_handler.capture_and_upload).start()
        return {"status": "success", "message": "Capture sequence initiated."}
    raise HTTPException(status_code=503, detail="Camera handler not available.")

# WebSocket 엔드포인트
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # 실시간 데이터 전송을 위한 WebSocket 연결.
    await connection_manager.connect(websocket)
    try:
        while True:
            # 클라이언트로부터 메시지를 받을 수도 있지만, 현재는 서버->클라이언트 단방향 전송만 구현
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)

# 백그라운드 작업
def broadcast_loop():
    # 일정 주기로 모든 WebSocket 클라이언트에게 상태를 브로드캐스트하는 루프.
    while True:
        # main.py에서 system_state가 초기화된 후에 루프 시작
        if system_state:
            state_data = system_state.get_full_state()
            # 비동기 함수를 동기 코드에서 실행하기 위한 트릭
            import asyncio
            asyncio.run(connection_manager.broadcast_state(state_data))
        time.sleep(2) # 2초마다 상태 전송

# --- 서버 실행 함수 ---
def run_api_server(state_instance, hardware_instance, camera_instance):
    # main.py에서 이 함수를 호출하여 API 서버를 실행합니다.
    global system_state, hardware_controller, camera_handler
    system_state = state_instance
    hardware_controller = hardware_instance
    camera_handler = camera_instance
    
    # 백그라운드에서 WebSocket 브로드캐스트 루프 시작
    threading.Thread(target=broadcast_loop, daemon=True).start()
    
    log.info("Starting API server with Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
