"""
T2P Compiler - TestSpec → PhoneAgent 指令编译器

将 TestSpec 编译为 PhoneAgent 可执行的 Task Bundle。
"""

__version__ = "0.1.0"

from t2p.models.task_bundle import TaskBundle, TaskConfig, PolicyConfig, CompileReport
from t2p.models.observation import ObservationSpec, Checkpoint, CompiledAssertion

__all__ = [
    "TaskBundle",
    "TaskConfig", 
    "PolicyConfig",
    "CompileReport",
    "ObservationSpec",
    "Checkpoint",
    "CompiledAssertion",
    "__version__",
]
