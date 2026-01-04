import asyncio
import subprocess
import logging
from datetime import datetime
from typing import Dict

from server.schemas.device import Device, DeviceStatus

logger = logging.getLogger(__name__)

class DeviceManager:
    def __init__(self):
        self._devices: Dict[str, Device] = {}
        self._polling_task = None
        self._running = False
        
    async def start(self):
        """启动设备轮询"""
        if self._running:
            return
        self._running = True
        self._polling_task = asyncio.create_task(self._poll_loop())
        logger.info("Device polling started")
        
    async def stop(self):
        """停止设备轮询"""
        self._running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
    
    def get_devices(self) -> list[Device]:
        """获取所有设备"""
        return list(self._devices.values())
    
    def get_device(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def lock_device(self, device_id: str, run_id: str) -> bool:
        """锁定设备"""
        device = self._devices.get(device_id)
        if not device:
            return False
        if device.status != DeviceStatus.FREE:
            return False
        
        device.status = DeviceStatus.RESERVED
        device.locked_by = run_id
        return True
    
    def unlock_device(self, device_id: str, run_id: str) -> bool:
        """解锁设备"""
        device = self._devices.get(device_id)
        if not device:
            return False
        if device.locked_by != run_id:
            return False
        
        device.status = DeviceStatus.FREE
        device.locked_by = None
        return True
        
    async def _poll_loop(self):
        while self._running:
            try:
                await self._update_devices()
            except Exception as e:
                logger.error(f"Error polling devices: {e}")
            await asyncio.sleep(3)
            
    async def _update_devices(self):
        # 执行 adb devices -l
        cmd = ["adb", "devices", "-l"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        output = stdout.decode("utf-8")
        
        current_ids = set()
        
        lines = output.strip().splitlines()
        # skip "List of devices attached"
        for line in lines[1:]:
            parts = line.strip().split()
            if not parts:
                continue
                
            device_id = parts[0]
            status = parts[1]
            
            # 过滤 emulator
            if device_id.startswith("emulator-"):
                continue
                
            current_ids.add(device_id)
            
            # 解析 model (e.g. model:Pixel_4)
            model = None
            for part in parts:
                if part.startswith("model:"):
                    model = part.split(":")[1]
            
            # Update or Create
            if device_id not in self._devices:
                self._devices[device_id] = Device(
                    id=device_id,
                    type="adb",
                    model=model,
                    status=DeviceStatus.FREE,
                    last_heartbeat=datetime.now()
                )
            else:
                dev = self._devices[device_id]
                dev.last_heartbeat = datetime.now()
                # 只有在 offline 时恢复，不覆盖 LOCKED 状态
                if dev.status == DeviceStatus.OFFLINE:
                     dev.status = DeviceStatus.FREE
        
        # 标记已断开的设备为 OFFLINE
        for dev_id, dev in self._devices.items():
            if dev_id not in current_ids and dev.status != DeviceStatus.OFFLINE:
                dev.status = DeviceStatus.OFFLINE
                logger.info(f"Device {dev_id} went offline")

# Singleton
device_manager = DeviceManager()
