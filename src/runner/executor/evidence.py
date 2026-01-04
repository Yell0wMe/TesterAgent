"""
Evidence Collector - 证据采集

采集截图和其他证据。
"""

import os
import json
from pathlib import Path
from datetime import datetime

from runner.executor.device import Device


class EvidenceCollector:
    """证据采集器"""
    
    def __init__(self, evidence_dir: str):
        """
        初始化
        
        Args:
            evidence_dir: 证据目录路径
        """
        self.evidence_dir = Path(evidence_dir)
        self.screenshots_dir = self.evidence_dir / "screenshots"
        self.logs_dir = self.evidence_dir / "logs"
        
        # 创建目录
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self._screenshot_counter = 0
    
    def capture_step_screenshot(self, device: Device, step_index: int) -> str | None:
        """
        采集步骤截图
        
        Args:
            device: 设备
            step_index: 步骤编号
            
        Returns:
            截图相对路径或 None
        """
        filename = f"step_{step_index:03d}.png"
        filepath = self.screenshots_dir / filename
        
        if device.screenshot(str(filepath)):
            return f"evidence/screenshots/{filename}"
        return None
    
    def capture_final_screenshot(self, device: Device) -> str | None:
        """采集最终截图"""
        filename = "final.png"
        filepath = self.screenshots_dir / filename
        
        if device.screenshot(str(filepath)):
            return f"evidence/screenshots/{filename}"
        return None
    
    def capture_checkpoint_screenshot(self, device: Device, checkpoint_id: str) -> str | None:
        """采集检查点截图"""
        filename = f"checkpoint_{checkpoint_id}.png"
        filepath = self.screenshots_dir / filename
        
        if device.screenshot(str(filepath)):
            return f"evidence/screenshots/{filename}"
        return None
    
    def save_logcat(self, content: str, filename: str = "logcat_tail.txt") -> str:
        """保存 logcat 日志"""
        filepath = self.logs_dir / filename
        filepath.write_text(content, encoding="utf-8")
        return f"evidence/logs/{filename}"
    
    def get_all_screenshots(self) -> list[str]:
        """获取所有截图文件"""
        screenshots = []
        for f in sorted(self.screenshots_dir.glob("*.png")):
            screenshots.append(f"evidence/screenshots/{f.name}")
        return screenshots
    
    def get_final_screenshot_path(self) -> str | None:
        """获取最终截图绝对路径"""
        final_path = self.screenshots_dir / "final.png"
        if final_path.exists():
            return str(final_path)
        return None
