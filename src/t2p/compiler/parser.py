"""
Parser/Normalizer - TestSpec 解析与校验

加载 TestSpec，校验必填字段，补充默认值。
"""

import hashlib
from pathlib import Path
from typing import Any

import yaml

from doc2spec.models.testspec import TestSpec
from t2p.models.task_bundle import DiagnosticItem, DiagnosticLevel


class ParseError(Exception):
    """解析错误"""
    pass


class SpecParser:
    """TestSpec 解析器"""
    
    def __init__(self, strict: bool = False):
        """
        初始化解析器
        
        Args:
            strict: 严格模式，缺失必填字段时抛出错误而非警告
        """
        self.strict = strict
        self.diagnostics: list[DiagnosticItem] = []
    
    def parse(self, spec: TestSpec) -> tuple[TestSpec, list[DiagnosticItem], str]:
        """
        解析并规范化 TestSpec
        
        Args:
            spec: 输入的 TestSpec
            
        Returns:
            tuple: (规范化后的 spec, 诊断信息, 输入哈希)
        """
        self.diagnostics = []
        
        # 计算输入哈希
        input_hash = self._compute_hash(spec)
        
        # 校验必填字段
        self._validate_required(spec)
        
        # 规范化处理
        normalized = self._normalize(spec)
        
        return normalized, self.diagnostics, input_hash
    
    def parse_file(self, path: str | Path) -> tuple[TestSpec, list[DiagnosticItem], str]:
        """从文件解析 TestSpec"""
        path = Path(path)
        
        if not path.exists():
            raise ParseError(f"文件不存在: {path}")
        
        spec = TestSpec.from_yaml_file(str(path))
        return self.parse(spec)
    
    def _compute_hash(self, spec: TestSpec) -> str:
        """计算 TestSpec 的哈希值"""
        content = spec.model_dump_json()
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
    
    def _validate_required(self, spec: TestSpec) -> None:
        """校验必填字段"""
        # goal 校验
        if not spec.goal.user_intent:
            self._add_diagnostic(
                DiagnosticLevel.ERROR if self.strict else DiagnosticLevel.WARNING,
                "P001",
                "goal.user_intent 为空",
                "goal.user_intent"
            )
        
        # assertions 校验
        if not spec.assertions.ui:
            self._add_diagnostic(
                DiagnosticLevel.ERROR,
                "P002",
                "assertions.ui 为空，至少需要 1 条 UI 断言",
                "assertions.ui"
            )
        
        # source 校验
        if not spec.source:
            self._add_diagnostic(
                DiagnosticLevel.WARNING,
                "P003",
                "source 为空，无法追溯",
                "source"
            )
    
    def _normalize(self, spec: TestSpec) -> TestSpec:
        """规范化处理"""
        updates = {}
        
        # 确保 budget 有合理默认值
        if spec.budget.max_steps <= 0:
            self._add_diagnostic(
                DiagnosticLevel.INFO,
                "N001",
                f"budget.max_steps={spec.budget.max_steps} 无效，已设为 40",
                "budget.max_steps"
            )
        
        if spec.budget.timeout_sec <= 0:
            self._add_diagnostic(
                DiagnosticLevel.INFO,
                "N002",
                f"budget.timeout_sec={spec.budget.timeout_sec} 无效，已设为 180",
                "budget.timeout_sec"
            )
        
        # steps 为空时添加诊断
        if not spec.steps:
            self._add_diagnostic(
                DiagnosticLevel.INFO,
                "N003",
                "steps 为空，将启用 agent 自规划模式",
                "steps"
            )
        
        return spec
    
    def _add_diagnostic(
        self, 
        level: DiagnosticLevel, 
        code: str, 
        message: str, 
        field: str | None = None
    ) -> None:
        """添加诊断项"""
        self.diagnostics.append(DiagnosticItem(
            level=level,
            code=code,
            message=message,
            field=field
        ))
