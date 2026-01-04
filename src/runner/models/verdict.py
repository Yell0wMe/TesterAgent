"""
Verdict 数据模型

定义断言判定结果。
"""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class VerdictStatus(str, Enum):
    """判定状态"""
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    SKIP = "SKIP"


class AssertionResult(BaseModel):
    """单条断言结果"""
    id: str
    original_id: str | None = None
    must: bool = True
    status: VerdictStatus
    evidence: str | None = None  # 截图路径
    why: str  # 可解释原因
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class VerdictMeta(BaseModel):
    """判定元数据"""
    judged_at: datetime = Field(default_factory=datetime.now)
    takeover_used: bool = False
    guards_triggered: bool = False
    duration_sec: float = 0.0
    engine: str = Field(default="text")


class Verdict(BaseModel):
    """
    Verdict - 断言判定结果
    
    Judge 输出，包含每条断言的可解释结果。
    """
    case_id: str
    run_id: str
    status: VerdictStatus
    summary: str
    assertions: list[AssertionResult] = Field(default_factory=list)
    meta: VerdictMeta = Field(default_factory=VerdictMeta)
    
    @property
    def pass_count(self) -> int:
        return sum(1 for a in self.assertions if a.status == VerdictStatus.PASS)
    
    @property
    def fail_count(self) -> int:
        return sum(1 for a in self.assertions if a.status == VerdictStatus.FAIL)
    
    @property
    def must_assertions(self) -> list[AssertionResult]:
        return [a for a in self.assertions if a.must]
    
    @classmethod
    def compute_status(cls, assertions: list[AssertionResult]) -> VerdictStatus:
        """计算最终状态"""
        must_results = [a for a in assertions if a.must]
        
        # 所有 must 断言通过 → PASS
        if all(a.status == VerdictStatus.PASS for a in must_results):
            return VerdictStatus.PASS
        
        # 有 BLOCKED → BLOCKED
        if any(a.status == VerdictStatus.BLOCKED for a in must_results):
            return VerdictStatus.BLOCKED
        
        # 其他情况 → FAIL
        return VerdictStatus.FAIL
