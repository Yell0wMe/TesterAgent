"""
Report 数据模型

定义报告结构。
"""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

from runner.models.verdict import VerdictStatus


class FailureCategory(str, Enum):
    """失败分类"""
    ASSERTION_FAILED = "assertion_failed"
    TIMEOUT = "timeout"
    DEVICE_DISCONNECT = "device_disconnect"
    GUARD_DENIED = "guard_denied"
    CRASH_SUSPECTED = "crash_suspected"
    UNKNOWN = "unknown"


class CaseResult(BaseModel):
    """单个用例结果"""
    case_id: str
    run_id: str
    status: VerdictStatus
    duration_sec: float = 0.0
    step_count: int = 0
    retry_count: int = 0
    takeover_used: bool = False
    failure_category: FailureCategory | None = None
    failed_assertions: list[str] = Field(default_factory=list)
    flaky_suspected: bool = False


class ReportSummary(BaseModel):
    """报告摘要"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    pass_rate: float = 0.0
    total_duration_sec: float = 0.0
    
    # 失败分类统计
    failure_breakdown: dict[str, int] = Field(default_factory=dict)
    
    # Flaky 统计
    flaky_count: int = 0


class Report(BaseModel):
    """
    Report - 测试报告
    
    汇总多个用例的执行结果。
    """
    report_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    runner_version: str = Field(default="0.1.0")
    
    summary: ReportSummary = Field(default_factory=ReportSummary)
    cases: list[CaseResult] = Field(default_factory=list)
    
    # 元数据
    device_info: dict = Field(default_factory=dict)
    environment: dict = Field(default_factory=dict)
    
    def compute_summary(self) -> None:
        """计算摘要"""
        self.summary.total = len(self.cases)
        self.summary.passed = sum(1 for c in self.cases if c.status == VerdictStatus.PASS)
        self.summary.failed = sum(1 for c in self.cases if c.status == VerdictStatus.FAIL)
        self.summary.blocked = sum(1 for c in self.cases if c.status == VerdictStatus.BLOCKED)
        self.summary.total_duration_sec = sum(c.duration_sec for c in self.cases)
        
        if self.summary.total > 0:
            self.summary.pass_rate = self.summary.passed / self.summary.total
        
        # 失败分类
        breakdown = {}
        for c in self.cases:
            if c.failure_category:
                cat = c.failure_category.value
                breakdown[cat] = breakdown.get(cat, 0) + 1
        self.summary.failure_breakdown = breakdown
        
        # Flaky 统计
        self.summary.flaky_count = sum(1 for c in self.cases if c.flaky_suspected)
