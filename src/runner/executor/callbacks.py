"""
Callbacks - 回调处理

处理 confirmation_callback 和 takeover_callback。
"""

import time
from datetime import datetime
from typing import Callable

from runner.models.run_artifact import EventRecord


class CallbackHandler:
    """回调处理器"""
    
    def __init__(
        self,
        auto_confirm: bool = True,
        auto_takeover: bool = True,
        takeover_timeout_sec: int = 300
    ):
        """
        初始化
        
        Args:
            auto_confirm: 自动确认（Mock 模式）
            auto_takeover: 自动接管（Mock 模式）
            takeover_timeout_sec: 接管超时秒数
        """
        self.auto_confirm = auto_confirm
        self.auto_takeover = auto_takeover
        self.takeover_timeout_sec = takeover_timeout_sec
        
        # 记录
        self.events: list[EventRecord] = []
        self.takeover_duration_sec = 0.0
        self.takeover_count = 0
        self.guards_triggered = False
    
    def confirmation_callback(self, reason: str) -> bool:
        """
        敏感操作确认回调
        
        Args:
            reason: 确认原因
            
        Returns:
            True 允许继续，False 拒绝
        """
        self.guards_triggered = True
        
        self.events.append(EventRecord(
            event="guard_prompt",
            reason=reason
        ))
        
        if self.auto_confirm:
            # Mock 模式：默认拒绝敏感操作
            self.events.append(EventRecord(
                event="guard_denied",
                reason=f"Auto-denied: {reason}"
            ))
            return False
        
        # 真实模式：等待用户输入
        print(f"\n⚠️  敏感操作确认: {reason}")
        response = input("允许继续? (y/N): ").strip().lower()
        
        allowed = response == "y"
        
        self.events.append(EventRecord(
            event="guard_allowed" if allowed else "guard_denied",
            reason=reason
        ))
        
        return allowed
    
    def takeover_callback(self, reason: str) -> None:
        """
        人工接管回调
        
        Args:
            reason: 接管原因
        """
        self.takeover_count += 1
        start_time = time.time()
        
        self.events.append(EventRecord(
            event="takeover_start",
            reason=reason
        ))
        
        if self.auto_takeover:
            # Mock 模式：模拟人工操作延迟
            time.sleep(0.5)
        else:
            # 真实模式：等待用户操作
            print(f"\n🔔 需要人工接管: {reason}")
            print("请在设备上完成操作后按 Enter 继续...")
            
            try:
                input()
            except KeyboardInterrupt:
                pass
        
        duration = time.time() - start_time
        self.takeover_duration_sec += duration
        
        self.events.append(EventRecord(
            event="takeover_end",
            reason=reason,
            data={"duration_sec": duration}
        ))
    
    def get_summary(self) -> dict:
        """获取回调摘要"""
        return {
            "takeover_count": self.takeover_count,
            "takeover_duration_sec": self.takeover_duration_sec,
            "guards_triggered": self.guards_triggered,
            "events_count": len(self.events)
        }
