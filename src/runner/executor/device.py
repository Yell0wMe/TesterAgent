"""
Device Manager - 设备管理

支持 Mock 设备和 ADB/HDC 设备接口。
"""

import os
import time
import random
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime


class Device(ABC):
    """设备抽象基类"""
    
    @property
    @abstractmethod
    def device_id(self) -> str:
        pass
    
    @property
    @abstractmethod
    def device_type(self) -> str:
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        pass
    
    @abstractmethod
    def screenshot(self, save_path: str) -> bool:
        pass
    
    @abstractmethod
    def tap(self, x: int, y: int) -> bool:
        pass
    
    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        pass
    
    @abstractmethod
    def input_text(self, text: str) -> bool:
        pass
    
    @abstractmethod
    def press_back(self) -> bool:
        pass
    
    @abstractmethod
    def press_home(self) -> bool:
        pass
    
    @abstractmethod
    def launch_app(self, package: str) -> bool:
        pass


class MockDevice(Device):
    """
    Mock 设备
    
    用于测试流程，不依赖真实设备。
    """
    
    def __init__(self, device_id: str = "mock_device_001"):
        self._device_id = device_id
        self._connected = True
        self._screen_counter = 0
    
    @property
    def device_id(self) -> str:
        return self._device_id
    
    @property
    def device_type(self) -> str:
        return "mock"
    
    def is_connected(self) -> bool:
        return self._connected
    
    def disconnect(self) -> None:
        """模拟断连"""
        self._connected = False
    
    def screenshot(self, save_path: str) -> bool:
        """生成模拟截图"""
        if not self._connected:
            return False
        
        # 创建目录
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 生成一个简单的占位图片（实际环境可以用 PIL 生成测试图）
        self._screen_counter += 1
        
        # 写入一个简单的文本文件作为占位（真实场景用 PNG）
        placeholder = f"MOCK_SCREENSHOT_{self._screen_counter}_{datetime.now().isoformat()}"
        
        # 模拟截图延迟
        time.sleep(0.05)
        
        # 创建一个空的 PNG 占位文件
        with open(save_path, "wb") as f:
            # 最小的 PNG 文件（1x1 透明像素）
            png_data = bytes([
                0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
                0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
                0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
                0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
                0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
                0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
                0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
                0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
                0x42, 0x60, 0x82
            ])
            f.write(png_data)
        
        return True
    
    def tap(self, x: int, y: int) -> bool:
        if not self._connected:
            return False
        time.sleep(0.02)  # 模拟延迟
        return True
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        if not self._connected:
            return False
        time.sleep(duration_ms / 1000 * 0.1)  # 模拟延迟
        return True
    
    def input_text(self, text: str) -> bool:
        if not self._connected:
            return False
        time.sleep(0.03)
        return True
    
    def press_back(self) -> bool:
        if not self._connected:
            return False
        time.sleep(0.02)
        return True
    
    def press_home(self) -> bool:
        if not self._connected:
            return False
        time.sleep(0.02)
        return True
    
    def launch_app(self, package: str) -> bool:
        if not self._connected:
            return False
        time.sleep(0.1)  # 模拟启动延迟
        return True


class DeviceManager:
    """设备管理器"""
    
    def __init__(self):
        self._devices: dict[str, Device] = {}
    
    def add_device(self, device: Device) -> None:
        """添加设备"""
        self._devices[device.device_id] = device
    
    def get_device(self, device_id: str) -> Device | None:
        """获取设备"""
        return self._devices.get(device_id)
    
    def get_mock_device(self, device_id: str = "mock") -> MockDevice:
        """获取或创建 Mock 设备"""
        if device_id not in self._devices:
            self._devices[device_id] = MockDevice(device_id)
        return self._devices[device_id]
    
    def list_devices(self) -> list[str]:
        """列出所有设备"""
        return list(self._devices.keys())
    
    def check_all_connected(self) -> dict[str, bool]:
        """检查所有设备连接状态"""
        return {did: d.is_connected() for did, d in self._devices.items()}
