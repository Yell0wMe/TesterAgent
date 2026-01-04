"""
Task Bundle 数据模型

定义 T2P 编译器的输出结构。
"""

from typing import Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class GuardLevel(str, Enum):
    """Guards 严格程度"""
    STRICT = "strict"      # 有风险就拦截
    CONFIRM = "confirm"    # 触发确认回调
    WARN = "warn"          # 仅警告


class RetryStrategy(str, Enum):
    """重试策略"""
    IMMEDIATE = "immediate"
    BACKOFF = "backoff"
    NONE = "none"


class AgentConfig(BaseModel):
    """PhoneAgent 配置"""
    max_steps: int = Field(default=40, description="最大步骤数")
    lang: str = Field(default="cn", description="语言 cn/en")
    system_prompt: str | None = Field(default=None, description="自定义系统提示词")


class RetryConfig(BaseModel):
    """重试配置"""
    max_attempts: int = Field(default=2)
    backoff_sec: int = Field(default=3)
    strategy: RetryStrategy = Field(default=RetryStrategy.BACKOFF)


class GuardRule(BaseModel):
    """单条 Guard 规则"""
    id: str
    name: str
    keywords: list[str] = Field(default_factory=list)
    level: GuardLevel = Field(default=GuardLevel.STRICT)


class TakeoverPoint(BaseModel):
    """接管点"""
    id: str
    trigger: str
    reason: str


class PolicyConfig(BaseModel):
    """策略配置（policy.json）"""
    guards: list[GuardRule] = Field(default_factory=list)
    guard_level: GuardLevel = Field(default=GuardLevel.STRICT)
    takeover_points: list[TakeoverPoint] = Field(default_factory=list)
    timeout_sec: int = Field(default=180)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    evidence_capture: list[str] = Field(default_factory=list)


class TaskConfig(BaseModel):
    """任务配置（task.json）"""
    spec_id: str
    goal: str
    agent_config: AgentConfig = Field(default_factory=AgentConfig)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    allow_self_planning: bool = Field(default=False)


class DiagnosticLevel(str, Enum):
    """诊断级别"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DiagnosticItem(BaseModel):
    """诊断项"""
    level: DiagnosticLevel
    code: str
    message: str
    field: str | None = None


class CompileReport(BaseModel):
    """编译报告（compile_report.json）"""
    compiler_version: str
    spec_id: str
    input_hash: str
    compiled_at: datetime = Field(default_factory=datetime.now)
    base_prompt_version: str = Field(default="v0.1")
    diagnostics: list[DiagnosticItem] = Field(default_factory=list)
    takeover_points_detected: list[str] = Field(default_factory=list)
    guard_triggers_detected: list[str] = Field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return any(d.level == DiagnosticLevel.ERROR for d in self.diagnostics)
    
    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.level == DiagnosticLevel.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.level == DiagnosticLevel.WARNING)


class TaskBundle(BaseModel):
    """Task Bundle - 编译产物"""
    spec_id: str
    bundle_id: str
    version: str = Field(default="0.1")
    
    # 核心内容
    task: TaskConfig
    system_prompt: str
    user_prompt: str
    
    # 结构化配置
    policy: PolicyConfig
    compile_report: CompileReport
    
    # 关联的 ObservationSpec（单独文件）
    observation_spec_ref: str = Field(default="observation_spec.json")
    
    def to_bundle_dir(self, base_dir: str) -> dict[str, str]:
        """返回各文件内容的映射"""
        import json
        
        return {
            "task.json": self.task.model_dump_json(indent=2),
            "system_prompt.txt": self.system_prompt,
            "user_task_prompt.txt": self.user_prompt,
            "policy.json": self.policy.model_dump_json(indent=2),
            "compile_report.json": self.compile_report.model_dump_json(indent=2),
        }
