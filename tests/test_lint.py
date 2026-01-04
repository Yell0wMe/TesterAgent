"""
Lint 模块单元测试
"""

import pytest
from doc2spec.models.testspec import (
    TestSpec, Source, Goal, UIAssertion, UIAssertionType,
    Assertions, Guards, Budget, Evidence, EvidenceItem, EvidenceType
)
from doc2spec.modules.lint import Linter, LintSeverity


def create_minimal_spec(spec_id: str = "TEST-TS-001", **overrides) -> TestSpec:
    """创建最小测试规格"""
    defaults = {
        "id": spec_id,
        "title": "测试用例",
        "source": [Source(doc_id="test.md", loc="P1")],
        "goal": Goal(user_intent="测试", success_state="成功"),
        "assertions": Assertions(
            ui=[UIAssertion(id="A1", type=UIAssertionType.TEXT_PRESENT, target="具体文案")]
        ),
    }
    defaults.update(overrides)
    return TestSpec(**defaults)


class TestLinter:
    """Linter 测试"""
    
    def test_valid_spec_passes(self):
        """测试有效规格通过"""
        spec = create_minimal_spec()
        linter = Linter(auto_fix=False)
        result = linter.lint(spec)
        
        assert not result.has_errors
    
    def test_auto_fix_evidence(self):
        """测试自动修复 evidence"""
        spec = create_minimal_spec(
            evidence=Evidence(required=[], optional=[])
        )
        
        linter = Linter(auto_fix=True)
        result = linter.lint(spec)
        
        # 应该自动添加 screenshot_final 和 screenshot_on_assertions
        required_types = {e.type for e in result.spec.evidence.required}
        assert EvidenceType.SCREENSHOT_FINAL in required_types
        assert EvidenceType.SCREENSHOT_ON_ASSERTIONS in required_types
        assert result.fixed_count >= 2
    
    def test_auto_fix_guards(self):
        """测试自动修复 guards"""
        spec = create_minimal_spec(
            guards=Guards(forbidden=[])
        )
        
        linter = Linter(auto_fix=True)
        result = linter.lint(spec)
        
        # 应该自动注入默认禁止操作
        assert len(result.spec.guards.forbidden) > 0
        assert "real_payment" in result.spec.guards.forbidden
    
    def test_warn_abstract_assertion(self):
        """测试警告抽象断言"""
        spec = create_minimal_spec(
            assertions=Assertions(
                ui=[UIAssertion(id="A1", type=UIAssertionType.TEXT_PRESENT, target="成功")]
            )
        )
        
        linter = Linter(auto_fix=False)
        result = linter.lint(spec)
        
        # 应该有警告
        warnings = [i for i in result.issues if i.severity == LintSeverity.WARNING]
        assert len(warnings) > 0
    
    def test_warn_vague_goal(self):
        """测试警告模糊目标"""
        spec = create_minimal_spec(
            goal=Goal(user_intent="浏览应用功能", success_state="查看完成")
        )
        
        linter = Linter(auto_fix=False)
        result = linter.lint(spec)
        
        # 应该有警告
        warnings = [i for i in result.issues if i.code == "W002"]
        assert len(warnings) > 0
    
    def test_filter_valid(self):
        """测试过滤有效规格"""
        specs = [
            create_minimal_spec("VALID-001"),
            create_minimal_spec("VALID-002"),
        ]
        
        linter = Linter(auto_fix=True)
        results = linter.lint_all(specs)
        valid = linter.filter_valid(results)
        
        assert len(valid) == 2
