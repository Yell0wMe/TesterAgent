"""
Bundles API - 获取可用的测试 Bundle 列表
"""

from fastapi import APIRouter, HTTPException
import os
import json
from pathlib import Path

router = APIRouter(prefix="/api/bundles", tags=["bundles"])

BUNDLES_DIR = "bundles"

@router.get("")
async def list_bundles(device_type: str = None):
    """列出所有可用的测试 Bundle"""
    bundles = []
    bundles_path = Path(BUNDLES_DIR)
    
    if not bundles_path.exists():
        return bundles
    
    for bundle_dir in bundles_path.iterdir():
        if bundle_dir.is_dir() and bundle_dir.name.endswith("_bundle"):
            try:
                # Try to read task.json for metadata
                task_path = bundle_dir / "task.json"
                if task_path.exists():
                    with open(task_path, "r", encoding="utf-8") as f:
                        task_data = json.load(f)
                    
                    # Extract preconditions for device_type filtering
                    preconditions = task_data.get("preconditions", {})
                    custom = preconditions.get("custom", {})
                    
                    bundle_info = {
                        "id": bundle_dir.name.replace("_bundle", ""),
                        "title": task_data.get("title", bundle_dir.name),
                        "bundle_path": str(bundle_dir),
                        "preconditions": preconditions,
                        "device_type": custom.get("device_type", "mobile")
                    }
                    
                    # Filter by device_type if specified
                    if device_type and bundle_info["device_type"] != device_type:
                        continue
                        
                    bundles.append(bundle_info)
            except Exception as e:
                # Skip bundles that can't be parsed
                print(f"Error parsing bundle {bundle_dir}: {e}")
                continue
    
    return bundles

@router.get("/{bundle_id}")
async def get_bundle(bundle_id: str):
    """获取单个 Bundle 详情"""
    bundle_path = Path(BUNDLES_DIR) / f"{bundle_id}_bundle"
    
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    task_path = bundle_path / "task.json"
    if not task_path.exists():
        raise HTTPException(status_code=404, detail="Bundle task.json not found")
    
    with open(task_path, "r", encoding="utf-8") as f:
        task_data = json.load(f)
    
    # Also try to load observation_spec
    obs_path = bundle_path / "observation_spec.json"
    observation_spec = None
    if obs_path.exists():
        with open(obs_path, "r", encoding="utf-8") as f:
            observation_spec = json.load(f)
    
    return {
        "id": bundle_id,
        "bundle_path": str(bundle_path),
        "task": task_data,
        "observation_spec": observation_spec
    }
