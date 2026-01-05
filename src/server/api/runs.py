from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import shutil
import logging

from server.services.task_manager import task_manager, manager

router = APIRouter(prefix="/api/runs", tags=["runs"])

class CreateRunRequest(BaseModel):
    doc_id: str
    device_id: str
    config: dict = {}

@router.post("")
async def create_run(request: CreateRunRequest):
    """创建任务"""
    run_id = await task_manager.create_run(request.doc_id, request.device_id, request.config)
    return {"run_id": run_id, "status": "pending"}

class CreateDirectRunRequest(BaseModel):
    instruction: str
    device_id: str
    config: dict = {}

@router.post("/direct")
async def create_direct_run(request: CreateDirectRunRequest):
    """创建并执行快捷 AI 任务"""
    run_id = await task_manager.create_direct_run(request.device_id, request.instruction, request.config)
    return {"run_id": run_id, "status": "pending"}


class CreateSpecRunRequest(BaseModel):
    bundle_path: str
    device_id: str
    config: dict = {}

@router.post("/spec")
async def create_spec_run(request: CreateSpecRunRequest):
    """使用指定 Bundle 执行完整 TestSpec"""
    run_id = await task_manager.create_spec_run(request.bundle_path, request.device_id, request.config)
    return {"run_id": run_id, "status": "pending"}


@router.post("/{run_id}/stop")
async def stop_run(run_id: str):
    """停止任务"""
    success = await task_manager.stop_run(run_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to stop run (id not found or not active)")
    return {"status": "stopped"}

@router.get("")
async def list_runs(status: str = None, limit: int = 20):
    """List all runs with optional filtering"""
    runs = task_manager.list_runs()
    # Basic filtering
    if status:
        runs = [r for r in runs if r.get("status") == status]
    
    # Sort by created_at desc
    runs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return runs[:limit]

@router.get("/{run_id}")
async def get_run(run_id: str):
    """获取任务详情"""
    run = task_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.delete("")
async def delete_all_runs():
    """清除所有历史任务（保留进行中）"""
    count = task_manager.delete_all_completed_runs()
    return {"status": "ok", "deleted_count": count}

@router.delete("/{run_id}")
async def delete_run(run_id: str):
    """删除历史任务"""
    success = task_manager.delete_run(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "deleted", "run_id": run_id}

@router.get("/{run_id}/artifacts")
async def get_run_artifacts(run_id: str):
    """获取任务产物清单"""
    run_dir = os.path.join("runs", run_id)
    # Simple recursive walk or just evidence dir
    evidence_dir = os.path.join(run_dir, "evidence")
    artifacts = []
    
    # 1. Report
    report_path = os.path.join(run_dir, "report.json")
    if os.path.exists(report_path):
        artifacts.append({"type": "report", "path": f"/artifacts/{run_id}/report.json", "name": "report.json"})
        
    # 2. Live Screenshot
    if os.path.exists(os.path.join(run_dir, "live.png")):
        artifacts.append({"type": "live", "path": f"/artifacts/{run_id}/live.png", "name": "live.png"})
        
    # 3. Screenshots
    screenshot_dir = os.path.join(evidence_dir, "screenshots")
    if os.path.exists(screenshot_dir):
        for f in sorted(os.listdir(screenshot_dir)):
            if f.endswith(".png"):
                 artifacts.append({
                     "type": "screenshot", 
                     "path": f"/artifacts/{run_id}/evidence/screenshots/{f}", 
                     "name": f
                 })
                 
    return artifacts

@router.get("/{run_id}/live")
async def get_run_live(run_id: str):
    """动态获取最新实时画面"""
    run_dir = os.path.join("runs", run_id)
    if not os.path.exists(run_dir):
        raise HTTPException(status_code=404, detail="Run not found")
        
    # Check for live.png first (backward compatibility)
    live_png = os.path.join(run_dir, "live.png")
    if os.path.exists(live_png):
        return FileResponse(live_png)
    
    # Fallback/Primary: Find latest screenshot in evidence/screenshots
    screenshot_dir = os.path.join(run_dir, "evidence", "screenshots")
    if os.path.exists(screenshot_dir):
        files = [f for f in os.listdir(screenshot_dir) if f.endswith(".png")]
        if files:
            # Sort by name (step_001, step_002...) or modification time
            # step_xxx naming ensures lexical sort works for order
            latest_file = sorted(files)[-1]
            return FileResponse(os.path.join(screenshot_dir, latest_file))
            
    # Default placeholder if no screenshots yet
    # Return 404 or a clear 1x1 pixel? 404 is better for frontend handling
    raise HTTPException(status_code=404, detail="No live view available")

@router.get("/{run_id}/download")
async def download_run(run_id: str):
    """下载任务产物 Zip"""
    import os
    run_dir = os.path.join("runs", run_id)
    if not os.path.exists(run_dir):
        raise HTTPException(status_code=404, detail="Run not found")
        
    # Create zip in tmp or just stream?
    # shutil.make_archive saves to file.
    zip_name = f"/tmp/{run_id}"
    shutil.make_archive(zip_name, 'zip', run_dir)
    return FileResponse(f"{zip_name}.zip", filename=f"run_{run_id}.zip")

@router.get("/{run_id}/verbose-log")
async def get_verbose_log(run_id: str):
    """获取完整的 Agent 执行日志"""
    run_dir = os.path.join("runs", run_id)
    log_path = os.path.join(run_dir, "agent_verbose.log")
    
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Verbose log not found")
    
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"log": content}

@router.get("/{run_id}/testcase")
async def get_testcase(run_id: str):
    """获取测试用例配置 (task.json)"""
    import json
    import glob
    run_dir = os.path.join("runs", run_id)
    
    # Find task.json in bundle_out/*/task.json
    pattern = os.path.join(run_dir, "bundle_out", "*", "task.json")
    matches = glob.glob(pattern)
    
    if not matches:
        raise HTTPException(status_code=404, detail="Testcase not found")
    
    with open(matches[0], "r", encoding="utf-8") as f:
        testcase = json.load(f)
    return testcase

@router.get("/{run_id}/report")
async def get_report(run_id: str):
    """获取测试判定报告 (verdict.json)"""
    import json
    run_dir = os.path.join("runs", run_id)
    
    # Check judge/verdict.json first
    verdict_path = os.path.join(run_dir, "judge", "verdict.json")
    if os.path.exists(verdict_path):
        with open(verdict_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback to report/report.json
    report_path = os.path.join(run_dir, "report", "report.json")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    raise HTTPException(status_code=404, detail="Report not found")
