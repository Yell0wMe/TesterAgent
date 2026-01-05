from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.services.device_manager import device_manager
from server.schemas.device import Device

router = APIRouter(prefix="/api/devices", tags=["devices"])

@router.get("", response_model=list[Device])
async def list_devices():
    """获取设备列表"""
    return device_manager.get_devices()

@router.get("/{device_id}", response_model=Device | None)
async def get_device(device_id: str):
    """获取设备详情"""
    return device_manager.get_device(device_id)

class UpdateRemarkRequest(BaseModel):
    remark: str

@router.put("/{device_id}/remark")
async def update_device_remark(device_id: str, request: UpdateRemarkRequest):
    """更新设备备注"""
    print(f"Received update remark request for {device_id}: {request.remark}")
    success = device_manager.update_remark(device_id, request.remark)
    if not success:
        print(f"Device {device_id} not found for remark update")
        raise HTTPException(status_code=404, detail="Device not found")
    print(f"Successfully updated remark for {device_id}")
    return {"status": "ok", "device_id": device_id, "remark": request.remark}
