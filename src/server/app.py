from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
load_dotenv()

from server.services.device_manager import device_manager
from server.services.task_manager import manager
from server.api import devices, runs, docs, settings, bundles

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await device_manager.start()
    yield
    # Shutdown
    await device_manager.stop()

app = FastAPI(
    title="TesterAgent Web Console",
    description="Real-device automation testing console",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(devices.router)
app.include_router(runs.router)
app.include_router(docs.router)
app.include_router(settings.router)
app.include_router(bundles.router)

# Mount Static Files for Runs (artifacts, screenshots, reports)
import os
os.makedirs("runs", exist_ok=True)
app.mount("/artifacts", StaticFiles(directory="runs"), name="runs")

# WebSocket Route
@app.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await manager.connect(run_id, websocket)
    try:
        while True:
            # 保持连接，接收客户端消息（可选）
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(run_id, websocket)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)
