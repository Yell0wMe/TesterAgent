"""
ObservationSpec 数据模型

定义断言编译后的观察任务结构。
"""

from typing import Any
from enum import Enum
from pydantic import BaseModel, Field


class CaptureType(str, Enum):
    """证据采集类型"""
    SCREENSHOT = "screenshot"
    FINAL_SCREEN = "final_screen"
    CURRENT_APP = "current_app"
    SCREENSHOT_SERIES = "screenshot_series_digest"
    LOGCAT_TAIL = "logcat_tail"
    UI_TREE = "ui_tree"


class CheckpointTrigger(str, Enum):
    """Checkpoint 触发时机"""
    START = "start"
    EACH_STEP = "each_step"
    ON_ASSERTION = "on_assertion"
    ON_CANDIDATE_SUCCESS = "on_candidate_success"
    ON_TAKEOVER = "on_takeover"
    ON_ERROR = "on_error"
    FINISH = "finish"


class CompiledAssertionType(str, Enum):
    """编译后的断言类型"""
    OCR_TEXT_CONTAINS = "ocr_text_contains"
    OCR_TEXT_NOT_CONTAINS = "ocr_text_not_contains"
    OCR_TEXT_EQUALS = "ocr_text_equals"
    UI_VISUAL_ELEMENT = "ui_visual_element"
    UI_ELEMENT_STATE = "ui_element_state"
    SCREEN_LAYOUT = "screen_layout"


class Checkpoint(BaseModel):
    """检查点 - 证据采集点"""
    id: str
    when: CheckpointTrigger
    capture: list[CaptureType] = Field(default_factory=list)
    assert_refs: list[str] = Field(default_factory=list, description="关联的断言 ID")
    description: str | None = None


class ElementSelector(BaseModel):
    """元素选择器"""
    text: str | None = None
    content_desc: str | None = None
    resource_id: str | None = None
    class_name: str | None = None


class CompiledAssertion(BaseModel):
    """编译后的断言"""
    id: str
    original_id: str  # 原 TestSpec 断言 ID
    type: CompiledAssertionType
    value: str | None = None
    selector: ElementSelector | None = None
    evidence_key: str  # 关联的证据 key，如 "CP_A1.screenshot"
    must: bool = True
    description: str | None = None


class ObservationSpec(BaseModel):
    """
    观察任务规格
    
    将 TestSpec 的断言编译为可机器判定的结构化证据采集任务。
    """
    spec_id: str
    version: str = Field(default="0.1")
    
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    assertions_compiled: list[CompiledAssertion] = Field(default_factory=list)
    
    # 额外配置
    capture_each_step: bool = Field(default=False)
    capture_on_error: bool = Field(default=True)
    logcat_window_sec: int = Field(default=30)
    
    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        for cp in self.checkpoints:
            if cp.id == checkpoint_id:
                return cp
        return None
    
    def get_assertion(self, assertion_id: str) -> CompiledAssertion | None:
        for a in self.assertions_compiled:
            if a.id == assertion_id:
                return a
        return None
    
    @classmethod
    def create_default_checkpoints(cls) -> list[Checkpoint]:
        """创建默认检查点"""
        return [
            Checkpoint(
                id="CP_START",
                when=CheckpointTrigger.START,
                capture=[CaptureType.SCREENSHOT, CaptureType.CURRENT_APP],
                description="任务开始时采集初始状态"
            ),
            Checkpoint(
                id="CP_FINAL",
                when=CheckpointTrigger.FINISH,
                capture=[CaptureType.FINAL_SCREEN, CaptureType.SCREENSHOT_SERIES],
                description="任务结束时采集最终状态"
            ),
        ]
