from fastapi import APIRouter
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
