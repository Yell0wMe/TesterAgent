"""
Run Artifact 数据模型

定义一次运行的完整证据包结构。
"""

from typing import Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """运行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    ERROR = "error"


class ActionType(str, Enum):
    """动作类型"""
    LAUNCH = "Launch"
    TAP = "Tap"
    TYPE = "Type"
    SWIPE = "Swipe"
    BACK = "Back"
    HOME = "Home"
    WAIT = "Wait"
    TAKE_OVER = "Take_over"
    LONG_PRESS = "Long_press"
    DOUBLE_TAP = "Double_tap"


class StepRecord(BaseModel):
    """步骤记录"""
    i: int = Field(..., description="步骤编号（0-indexed）")
    ts: datetime = Field(default_factory=datetime.now, description="时间戳")
    action: dict = Field(..., description="动作（name, args）")
    screen: str | None = Field(default=None, description="截图路径")
    status: str = Field(default="ok", description="状态 ok/error/timeout")
    latency_ms: int = Field(default=0, description="耗时毫秒")
    error: str | None = Field(default=None, description="错误信息")
    
    def to_jsonl(self) -> str:
        """转为 JSONL 格式"""
        return self.model_dump_json()


class EventRecord(BaseModel):
    """事件记录（非动作事件）"""
    ts: datetime = Field(default_factory=datetime.now)
    event: str  # takeover_start, takeover_end, guard_prompt, guard_denied, etc.
    reason: str | None = None
    data: dict = Field(default_factory=dict)


class RunMeta(BaseModel):
    """运行元数据"""
    run_id: str
    case_id: str
    bundle_id: str
    device_id: str = Field(default="mock")
    device_type: str = Field(default="mock")  # adb/hdc/mock
    model: str = Field(default="mock")
    lang: str = Field(default="cn")
    max_steps: int = Field(default=40)
    timeout_sec: int = Field(default=180)
    
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None
    duration_sec: float = Field(default=0.0)
    takeover_duration_sec: float = Field(default=0.0)
    takeover_count: int = Field(default=0)
    
    status: RunStatus = Field(default=RunStatus.PENDING)
    exit_reason: str | None = None
    
    # 环境信息
    compiler_version: str = Field(default="0.1.0")
    runner_version: str = Field(default="0.1.0")


class RunArtifact(BaseModel):
    """
    Run Artifact - 一次运行的完整证据包
    
    对应目录结构:
    runs/{run_id}/
      meta.json
      steps.jsonl
      evidence/screenshots/...
      judge/verdict.json
      report/...
    """
    meta: RunMeta
    steps: list[StepRecord] = Field(default_factory=list)
    events: list[EventRecord] = Field(default_factory=list)
    
    # 路径引用
    artifact_dir: str | None = None
    evidence_dir: str | None = None
    verdict_path: str | None = None
    
    @property
    def step_count(self) -> int:
        return len(self.steps)
    
    @property
    def is_finished(self) -> bool:
        return self.meta.status not in [RunStatus.PENDING, RunStatus.RUNNING]
    
    def add_step(self, action: dict, screen: str | None = None, latency_ms: int = 0) -> StepRecord:
        """添加步骤"""
        step = StepRecord(
            i=len(self.steps),
            action=action,
            screen=screen,
            latency_ms=latency_ms
        )
        self.steps.append(step)
        return step
    
    def add_event(self, event: str, reason: str | None = None, **data) -> EventRecord:
        """添加事件"""
        ev = EventRecord(event=event, reason=reason, data=data)
        self.events.append(ev)
        return ev
    
    def finish(self, status: RunStatus, reason: str | None = None) -> None:
        """完成运行"""
        self.meta.finished_at = datetime.now()
        self.meta.status = status
        self.meta.exit_reason = reason
        if self.meta.started_at:
            delta = self.meta.finished_at - self.meta.started_at
            self.meta.duration_sec = delta.total_seconds()
