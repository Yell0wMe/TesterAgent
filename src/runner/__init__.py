"""
Runner - 测试执行与判定框架

执行 Task Bundle，采集证据，判定断言，生成报告。
"""

__version__ = "0.1.0"

from runner.models.run_artifact import RunArtifact, RunMeta, StepRecord, RunStatus
from runner.models.verdict import Verdict, AssertionResult

__all__ = [
    "RunArtifact",
    "RunMeta",
    "StepRecord",
    "RunStatus",
    "Verdict",
    "AssertionResult",
    "__version__",
]
