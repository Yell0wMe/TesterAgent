"""
ObservationCompiler - 断言编译

将 TestSpec 的 Assertions 编译为 ObservationSpec。
"""

from doc2spec.models.testspec import TestSpec, UIAssertion, UIAssertionType, MatchMode
from t2p.models.observation import (
    ObservationSpec, Checkpoint, CompiledAssertion,
    CheckpointTrigger, CaptureType, CompiledAssertionType, ElementSelector
)


# 断言类型映射
ASSERTION_TYPE_MAP = {
    UIAssertionType.TEXT_PRESENT: CompiledAssertionType.OCR_TEXT_CONTAINS,
    UIAssertionType.TEXT_ABSENT: CompiledAssertionType.OCR_TEXT_NOT_CONTAINS,
    UIAssertionType.TOAST_PRESENT: CompiledAssertionType.OCR_TEXT_CONTAINS,
    UIAssertionType.SCREEN_LANDMARK: CompiledAssertionType.UI_VISUAL_ELEMENT,
    UIAssertionType.ELEMENT_STATE: CompiledAssertionType.UI_ELEMENT_STATE,
    UIAssertionType.COUNT: CompiledAssertionType.SCREEN_LAYOUT,
}


class ObservationCompiler:
    """断言编译器"""
    
    def __init__(self):
        self._assertion_counter = 0
    
    def compile(self, spec: TestSpec) -> ObservationSpec:
        """
        编译 TestSpec 的断言为 ObservationSpec
        
        Args:
            spec: TestSpec
            
        Returns:
            ObservationSpec
        """
        self._assertion_counter = 0
        
        # 创建检查点
        checkpoints = self._create_checkpoints(spec)
        
        # 编译断言
        compiled_assertions = self._compile_assertions(spec)
        
        # 确定是否每步截图
        capture_each_step = self._should_capture_each_step(spec)
        
        return ObservationSpec(
            spec_id=spec.id,
            checkpoints=checkpoints,
            assertions_compiled=compiled_assertions,
            capture_each_step=capture_each_step,
            capture_on_error=True,
        )
    
    def _create_checkpoints(self, spec: TestSpec) -> list[Checkpoint]:
        """创建检查点"""
        checkpoints = []
        
        # 开始检查点
        checkpoints.append(Checkpoint(
            id="CP_START",
            when=CheckpointTrigger.START,
            capture=[CaptureType.SCREENSHOT, CaptureType.CURRENT_APP],
            description="任务开始时采集初始状态"
        ))
        
        # 每步检查点（可选）
        evidence_types = [e.type.value for e in spec.evidence.required]
        if "screenshot_each_step" in evidence_types:
            checkpoints.append(Checkpoint(
                id="CP_STEP",
                when=CheckpointTrigger.EACH_STEP,
                capture=[CaptureType.SCREENSHOT],
                description="每步操作后采集截图"
            ))
        
        # 断言检查点
        assertion_ids = [a.id for a in spec.assertions.ui]
        checkpoints.append(Checkpoint(
            id="CP_ASSERTION",
            when=CheckpointTrigger.ON_ASSERTION,
            capture=[CaptureType.SCREENSHOT],
            assert_refs=assertion_ids,
            description="断言验证时采集截图"
        ))
        
        # 错误检查点
        checkpoints.append(Checkpoint(
            id="CP_ERROR",
            when=CheckpointTrigger.ON_ERROR,
            capture=[CaptureType.SCREENSHOT, CaptureType.LOGCAT_TAIL],
            description="发生错误时采集截图和日志"
        ))
        
        # 最终检查点
        checkpoints.append(Checkpoint(
            id="CP_FINAL",
            when=CheckpointTrigger.FINISH,
            capture=[CaptureType.FINAL_SCREEN, CaptureType.SCREENSHOT_SERIES],
            description="任务结束时采集最终状态"
        ))
        
        return checkpoints
    
    def _compile_assertions(self, spec: TestSpec) -> list[CompiledAssertion]:
        """编译断言"""
        compiled = []
        
        for assertion in spec.assertions.ui:
            compiled_assertion = self._compile_single_assertion(assertion)
            compiled.append(compiled_assertion)
        
        return compiled
    
    def _compile_single_assertion(self, assertion: UIAssertion) -> CompiledAssertion:
        """编译单个断言"""
        self._assertion_counter += 1
        
        # 映射断言类型
        compiled_type = ASSERTION_TYPE_MAP.get(
            assertion.type, 
            CompiledAssertionType.OCR_TEXT_CONTAINS
        )
        
        # 根据类型创建编译后的断言
        if compiled_type in [
            CompiledAssertionType.OCR_TEXT_CONTAINS,
            CompiledAssertionType.OCR_TEXT_NOT_CONTAINS,
            CompiledAssertionType.OCR_TEXT_EQUALS,
        ]:
            # 文本类断言
            return CompiledAssertion(
                id=f"CA_{self._assertion_counter:03d}",
                original_id=assertion.id,
                type=compiled_type,
                value=assertion.target,
                evidence_key="CP_ASSERTION.screenshot",
                must=assertion.must,
                description=assertion.description or f"验证文本: {assertion.target}"
            )
        else:
            # 元素类断言
            return CompiledAssertion(
                id=f"CA_{self._assertion_counter:03d}",
                original_id=assertion.id,
                type=compiled_type,
                selector=ElementSelector(text=assertion.target),
                evidence_key="CP_ASSERTION.screenshot",
                must=assertion.must,
                description=assertion.description or f"验证元素: {assertion.target}"
            )
    
    def _should_capture_each_step(self, spec: TestSpec) -> bool:
        """判断是否需要每步截图"""
        for evidence in spec.evidence.required:
            if evidence.type.value == "screenshot_each_step":
                return True
        return False
