"""
Synthesis Prompt - B阶段规格合成提示词

用于将 RequirementItem 转换为 TestSpec YAML。
"""

SYNTHESIS_SYSTEM_PROMPT = """你是一个专业的测试规格生成器。你的任务是将需求条目转换为结构化的 TestSpec。

**规则：**
1. 输出必须是严格的 YAML 格式
2. 不要输出任何解释文字，只输出 YAML
3. 必须包含所有必填字段
4. 断言必须具体可判定，避免过于抽象的描述

**TestSpec 必填字段：**
- version: "0.1"
- id: 唯一标识符
- title: 用例标题
- source: 文档引用（doc_id + loc）
- goal: 用户目标（user_intent + success_state）
- assertions.ui: 至少1条UI断言
- guards.forbidden: 禁止操作列表
- budget: 执行预算（max_steps, timeout_sec, retries）
- evidence.required: 证据采集要求

**断言类型：**
- ui_text_present: 页面出现文本
- ui_text_absent: 页面不应出现文本
- ui_toast_present: 出现 Toast 提示
- ui_screen_landmark: 页面地标
- ui_element_state: 按钮状态
- ui_count: 列表项数量"""


def get_synthesis_prompt() -> str:
    """获取规格合成提示词"""
    return """请将以下需求条目转换为 TestSpec YAML 格式。

**输出格式示例**:
```yaml
version: "0.1"
id: "PRD-TS-001"
title: "用户登录后进入首页"
source:
  - doc_id: "PRD_v1.md"
    loc: "H2: 登录 > 成功标准 / P3"
goal:
  user_intent: "完成登录并进入首页"
  success_state: "首页可见且处于已登录状态"
preconditions:
  account:
    state: "logged_out"
  device:
    network: "any"
  app:
    install_state: "installed"
    cold_start: true
assertions:
  ui:
    - id: "A1"
      type: "ui_text_present"
      target: "首页"
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
tags: ["p0", "auth"]
notes: {}
```

**需求条目**:
"""
