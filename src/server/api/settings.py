
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from server.services.settings_manager import settings_manager
import os

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    zhipu_api_key: Optional[str] = None
    zhipu_model: Optional[str] = None

@router.get("")
async def get_settings():
    """获取当前设置"""
    # 获取 API Key，如果存在则脱敏返回
    api_key = settings_manager.get_setting("zhipu_api_key")
    if not api_key:
        api_key = os.getenv("ZHIPU_API_KEY")
    
    masked_key = ""
    if api_key:
        if len(api_key) > 8:
            masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        else:
            masked_key = "********"

    # 获取 Model 配置
    model = settings_manager.get_setting("zhipu_model") or os.getenv("ZHIPU_MODEL") or "glm-4"

    return {
        "zhipu_api_key_masked": masked_key,
        "has_api_key": bool(api_key),
        "zhipu_model": model
    }

@router.put("")
async def update_settings(settings: SettingsUpdate):
    """更新设置"""
    if settings.zhipu_api_key is not None:
        settings_manager.set_setting("zhipu_api_key", settings.zhipu_api_key)
    
    if settings.zhipu_model is not None:
        settings_manager.set_setting("zhipu_model", settings.zhipu_model)
    
    return {"status": "ok", "message": "Settings updated"}
