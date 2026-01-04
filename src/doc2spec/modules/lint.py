"""
Lint 模块 - 校验与自动修复
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from doc2spec.models.testspec import (
    TestSpec, Evidence, EvidenceItem, EvidenceType,
    Guards, SafetyMode, DEFAULT_FORBIDDEN_OPERATIONS,
)

logger = logging.getLogger(__name__)


class LintSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintIssue:
    severity: LintSeverity
    code: str
    message: str
    field: str
    spec_id: str
    auto_fixed: bool = False


@dataclass
class LintResult:
    spec: TestSpec
    issues: list[LintIssue] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return any(i.severity == LintSeverity.ERROR for i in self.issues)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == LintSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == LintSeverity.WARNING)
    
    @property
    def fixed_count(self) -> int:
        return sum(1 for i in self.issues if i.auto_fixed)


ABSTRACT_TERMS = ["成功", "完成", "已提交", "ok", "success", "done"]
VAGUE_GOAL_TERMS = ["浏览应用", "体验流程", "使用功能", "测试功能"]


class Linter:
    def __init__(self, auto_fix: bool = True):
        self.auto_fix = auto_fix
    
    def lint(self, spec: TestSpec) -> LintResult:
        issues: list[LintIssue] = []
        current_spec = spec
        
        # Error checks
        current_spec = self._check_ui_assertions(current_spec, issues)
        current_spec = self._check_budget(current_spec, issues)
        
        # AutoFix
        if self.auto_fix:
            current_spec = self._fix_evidence(current_spec, issues)
            current_spec = self._fix_guards(current_spec, issues)
        
        # Warnings
        current_spec = self._warn_abstract(current_spec, issues)
        current_spec = self._warn_vague_goal(current_spec, issues)
        
        return LintResult(spec=current_spec, issues=issues)
    
    def lint_all(self, specs: list[TestSpec]) -> list[LintResult]:
        return [self.lint(spec) for spec in specs]
    
    def filter_valid(self, results: list[LintResult]) -> list[TestSpec]:
        return [r.spec for r in results if not r.has_errors]
    
    def _check_ui_assertions(self, spec: TestSpec, issues: list[LintIssue]) -> TestSpec:
        if not spec.assertions.ui:
            issues.append(LintIssue(
                severity=LintSeverity.ERROR, code="E001",
                message="assertions.ui 为空", field="assertions.ui", spec_id=spec.id
            ))
        return spec
    
    def _check_budget(self, spec: TestSpec, issues: list[LintIssue]) -> TestSpec:
        if spec.budget.max_steps <= 0:
            issues.append(LintIssue(
                severity=LintSeverity.ERROR, code="E002",
                message="budget.max_steps 必须大于 0", field="budget.max_steps", spec_id=spec.id
            ))
        if spec.budget.timeout_sec <= 0:
            issues.append(LintIssue(
                severity=LintSeverity.ERROR, code="E003",
                message="budget.timeout_sec 必须大于 0", field="budget.timeout_sec", spec_id=spec.id
            ))
        return spec
    
    def _fix_evidence(self, spec: TestSpec, issues: list[LintIssue]) -> TestSpec:
        required_types = {e.type for e in spec.evidence.required}
        new_required = list(spec.evidence.required)
        
        if EvidenceType.SCREENSHOT_FINAL not in required_types:
            new_required.append(EvidenceItem(type=EvidenceType.SCREENSHOT_FINAL))
            issues.append(LintIssue(
                severity=LintSeverity.INFO, code="F001",
                message="自动添加 screenshot_final", field="evidence.required",
                spec_id=spec.id, auto_fixed=True
            ))
        
        if EvidenceType.SCREENSHOT_ON_ASSERTIONS not in required_types:
            new_required.append(EvidenceItem(type=EvidenceType.SCREENSHOT_ON_ASSERTIONS))
            issues.append(LintIssue(
                severity=LintSeverity.INFO, code="F002",
                message="自动添加 screenshot_on_assertions", field="evidence.required",
                spec_id=spec.id, auto_fixed=True
            ))
        
        if len(new_required) > len(spec.evidence.required):
            new_evidence = Evidence(required=new_required, optional=spec.evidence.optional)
            spec = spec.model_copy(update={"evidence": new_evidence})
        
        return spec
    
    def _fix_guards(self, spec: TestSpec, issues: list[LintIssue]) -> TestSpec:
        if not spec.guards.forbidden:
            new_guards = Guards(forbidden=DEFAULT_FORBIDDEN_OPERATIONS.copy(), safety_mode=SafetyMode.STRICT)
            spec = spec.model_copy(update={"guards": new_guards})
            issues.append(LintIssue(
                severity=LintSeverity.INFO, code="F003",
                message="自动注入默认 guards.forbidden", field="guards.forbidden",
                spec_id=spec.id, auto_fixed=True
            ))
        return spec
    
    def _warn_abstract(self, spec: TestSpec, issues: list[LintIssue]) -> TestSpec:
        for a in spec.assertions.ui:
            if any(t in a.target.lower() for t in ABSTRACT_TERMS):
                issues.append(LintIssue(
                    severity=LintSeverity.WARNING, code="W001",
                    message=f"断言 '{a.target}' 过于抽象", field=f"assertions.ui[{a.id}]",
                    spec_id=spec.id
                ))
        return spec
    
    def _warn_vague_goal(self, spec: TestSpec, issues: list[LintIssue]) -> TestSpec:
        if any(t in spec.goal.user_intent for t in VAGUE_GOAL_TERMS):
            issues.append(LintIssue(
                severity=LintSeverity.WARNING, code="W002",
                message="goal.user_intent 过于宽泛", field="goal.user_intent", spec_id=spec.id
            ))
        return spec


def lint_specs(specs: list[TestSpec], auto_fix: bool = True) -> tuple[list[TestSpec], list[LintResult]]:
    linter = Linter(auto_fix=auto_fix)
    results = linter.lint_all(specs)
    valid_specs = linter.filter_valid(results)
    return valid_specs, results
