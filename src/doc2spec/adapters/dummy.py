"""
Dummy LLM Adapter

用于调试的模拟适配器，返回预设响应。
"""

import json
from doc2spec.adapters.base import LLMAdapter


class DummyAdapter(LLMAdapter):
    """Dummy 适配器 - 用于调试"""
    
    def __init__(self, mode: str = "mining"):
        """
        初始化
        
        Args:
            mode: 模式 - "mining" 返回 JSON, "synthesis" 返回 YAML
        """
        self.mode = mode
    
    @property
    def name(self) -> str:
        return f"dummy-{self.mode}"
    
    def complete(self, prompt: str, input_text: str) -> str:
        if self.mode == "mining":
            return self._mining_response(input_text)
        else:
            return self._synthesis_response(input_text)
    
    def _mining_response(self, input_text: str) -> str:
        """返回模拟的需求挖掘结果"""
        result = [{
            "req_id": None,
            "req_title": "示例需求",
            "user_goal": "完成示例操作",
            "success_ui": ["操作成功提示"],
            "explicit_steps": ["步骤1", "步骤2"],
            "preconditions": ["已登录"],
            "verifiable_signals": [],
            "exceptions": ["网络异常时显示错误"],
            "danger_ops": [],
            "paragraph_index": 1,
            "priority": "P1",
            "category": "功能测试"
        }]
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def _synthesis_response(self, input_text: str) -> str:
        """返回模拟的规格合成结果"""
        return '''version: "0.1"
id: "DUMMY-TS-001"
title: "示例测试用例"
source:
  - doc_id: "dummy"
    loc: "H2: 示例 / P1"
goal:
  user_intent: "完成示例操作"
  success_state: "显示操作成功提示"
assertions:
  ui:
    - id: "A1"
      type: "ui_text_present"
      target: "操作成功"
      match: "contains"
      must: true
  verifiable: []
guards:
  forbidden:
    - "real_payment"
    - "account_deletion"
  safety_mode: "strict"
budget:
  max_steps: 40
  timeout_sec: 180
  retries:
    max_attempts: 2
    retry_on: ["timeout", "blocked_by_popup"]
    backoff_sec: 3
evidence:
  required:
    - type: "screenshot_final"
    - type: "screenshot_on_assertions"
  optional: []
tags: ["p1", "demo"]
notes: {}
'''
