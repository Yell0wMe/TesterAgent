"""
TestSpec 模型单元测试
"""

import pytest
import yaml
from doc2spec.models.testspec import (
    TestSpec, Source, Goal, UIAssertion, UIAssertionType, 
    MatchMode, Assertions, Guards, Budget, Evidence, EvidenceItem, EvidenceType
)


class TestTestSpec:
    """TestSpec 模型测试"""
    
    def test_create_minimal_spec(self):
        """测试创建最小合规的 TestSpec"""
        spec = TestSpec(
            id="TEST-TS-001",
            title="测试用例",
            source=[Source(doc_id="test.md", loc="H1: Test / P1")],
            goal=Goal(user_intent="完成测试", success_state="测试成功"),
            assertions=Assertions(
                ui=[UIAssertion(
                    id="A1",
                    type=UIAssertionType.TEXT_PRESENT,
                    target="成功"
                )]
            )
        )
        
        assert spec.id == "TEST-TS-001"
        assert spec.version == "0.1"
        assert len(spec.source) == 1
        assert len(spec.assertions.ui) == 1
    
    def test_spec_with_all_fields(self):
        """测试包含所有字段的 TestSpec"""
        spec = TestSpec(
            id="TEST-TS-002",
            title="完整测试用例",
            source=[Source(doc_id="test.md", loc="H1: Test", quote="原文引用")],
            goal=Goal(user_intent="完成操作", success_state="显示成功提示"),
            assertions=Assertions(
                ui=[
                    UIAssertion(id="A1", type=UIAssertionType.TEXT_PRESENT, target="成功"),
                    UIAssertion(id="A2", type=UIAssertionType.TOAST_PRESENT, target="提示")
                ]
            ),
            guards=Guards(forbidden=["real_payment"]),
            budget=Budget(max_steps=50, timeout_sec=200),
            evidence=Evidence(
                required=[EvidenceItem(type=EvidenceType.SCREENSHOT_FINAL)]
            ),
            tags=["p0", "smoke"]
        )
        
        assert len(spec.assertions.ui) == 2
        assert spec.budget.max_steps == 50
        assert "p0" in spec.tags
    
    def test_yaml_export(self):
        """测试 YAML 导出"""
        spec = TestSpec(
            id="TEST-TS-003",
            title="YAML测试",
            source=[Source(doc_id="test.md", loc="P1")],
            goal=Goal(user_intent="测试", success_state="成功"),
            assertions=Assertions(
                ui=[UIAssertion(id="A1", type=UIAssertionType.TEXT_PRESENT, target="成功")]
            )
        )
        
        yaml_str = spec.model_dump_yaml()
        
        assert "version:" in yaml_str
        assert "TEST-TS-003" in yaml_str
        assert "ui_text_present" in yaml_str
    
    def test_yaml_import(self):
        """测试 YAML 导入"""
        yaml_str = """
version: "0.1"
id: "IMPORT-TS-001"
title: "导入测试"
source:
  - doc_id: "test.md"
    loc: "P1"
goal:
  user_intent: "测试导入"
  success_state: "导入成功"
assertions:
  ui:
    - id: "A1"
      type: "ui_text_present"
      target: "成功"
      match: "contains"
      must: true
"""
        spec = TestSpec.from_yaml(yaml_str)
        
        assert spec.id == "IMPORT-TS-001"
        assert spec.assertions.ui[0].target == "成功"
    
    def test_empty_ui_assertions_raises_error(self):
        """测试空 UI 断言抛出错误"""
        with pytest.raises(ValueError):
            TestSpec(
                id="TEST-TS-ERR",
                title="错误测试",
                source=[Source(doc_id="test.md", loc="P1")],
                goal=Goal(user_intent="测试", success_state="成功"),
                assertions=Assertions(ui=[])  # 空断言应该报错
            )


class TestUIAssertion:
    """UI 断言测试"""
    
    def test_assertion_types(self):
        """测试各种断言类型"""
        types = [
            UIAssertionType.TEXT_PRESENT,
            UIAssertionType.TEXT_ABSENT,
            UIAssertionType.TOAST_PRESENT,
            UIAssertionType.SCREEN_LANDMARK,
            UIAssertionType.ELEMENT_STATE,
            UIAssertionType.COUNT,
        ]
        
        for i, t in enumerate(types):
            assertion = UIAssertion(id=f"A{i}", type=t, target="test")
            assert assertion.type == t
    
    def test_match_modes(self):
        """测试匹配模式"""
        for mode in [MatchMode.CONTAINS, MatchMode.EQUALS, MatchMode.REGEX]:
            assertion = UIAssertion(
                id="A1",
                type=UIAssertionType.TEXT_PRESENT,
                target="test",
                match=mode
            )
            assert assertion.match == mode
