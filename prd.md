# PRD：Doc → TestSpec 通用编译器（文档驱动的手机端自动化测试规格生成）

版本：v1.0（闭环可交付）
负责人：你（产品）/ 技术负责人（待定）
目标读者：后端/算法/测试/客户端工程师（“一看就知道要做什么”）

---

## 1. 背景与问题

现在想用“手机操作 AI”（如智谱开源 Open-AutoGLM 的 PhoneAgent）做端到端自动化测试，但直接把 PRD/开发文档喂给 Agent 会产生两个致命问题：

1. **不可判定**：Agent 做完了，你不知道算不算成功（缺少结构化断言与证据）。
2. **不可追溯/不可复现**：失败时不知道依据哪条需求、哪一步出错、如何复现。

因此需要一个通用的“编译器层”：
把任意形态的文档（PRD/纪要/接口说明/release note）**编译**成统一结构的 **TestSpec DSL（验收契约）**，为后续执行层（PhoneAgent）与判定层（Judge）提供机器可消费的输入。

---

## 2. 产品定义

### 2.1 产品名称

**Doc2Spec**（文档到测试规格编译器）

### 2.2 一句话描述

将自然语言产品/研发文档自动转换为结构化 TestSpec（包含目标、前置条件、断言、证据、风险禁止项、预算与重试策略），形成可执行、可判定、可追溯的验收契约。

---

## 3. 目标与成功标准

### 3.1 目标（必须达成）

* **G1：通用输入 → 统一输出**
  支持把 Markdown/TXT 文档编译为 TestSpec（YAML/JSON）
* **G2：结构化可判定**
  每条 TestSpec 至少包含 1 条 UI 断言 + 证据采集要求
* **G3：闭环可落盘**
  输出可用于后续 Runner 执行与 Judge 判定（即使暂未实现执行层，也要保证接口契约完整）
* **G4：可追溯**
  每条 TestSpec 必须携带 source 引用（doc_id + loc + quote 可选）

### 3.2 量化成功指标（上线 2 周内）

* 自动生成的 TestSpec 中：

  * 100% 通过 Schema 校验
  * ≥95% 通过 Lint（剩余需人工修复的可解释）
* 从 1 份 PRD（3~10页文字）生成：

  * 30~150 条可用 TestSpec（取决于粒度）
* 人工修订成本：

  * 单条 TestSpec 人工 review/修正 ≤ 2 分钟（重点修正断言）

---

## 4. 用户与使用场景

### 4.1 目标用户

* 测试工程师：想快速把需求变成自动化用例规格
* 研发/PM：想要“需求 → 验收契约 → 可回归”的链路
* 平台工程师：建设通用自动化测试平台

### 4.2 核心场景

* S1：新功能 PRD 出来后，自动生成回归用例规格
* S2：release note / bugfix 描述，自动生成“回归验证”规格
* S3：接口/错误码文档，补充可验证断言（非必须）

---

## 5. 范围与非范围

### 5.1 本期范围（v1.0）

* 文档输入：**Markdown / TXT**（UTF-8）
* 编译输出：**TestSpec YAML**（同时可导出 JSON）
* 编译流程：Normalize → Requirement Mining → Spec Synthesis → Lint+AutoFix → Export
* LLM 支持：抽象为 LLM Adapter（可接智谱 API、本地模型、企业网关）
* 工具形态：CLI（命令行）+ 可选本地 HTTP 服务（后续）

### 5.2 非范围（v1.0 不做，但需留接口）

* PDF/DOCX 解析（v1.1+）
* RAG 知识库检索（v1.2+）
* 执行层 PhoneAgent Runner（第 2 层，后续 PRD）
* 判定层 Oracle/Judge（第 3 层，后续 PRD）
* GUI 管理后台（后续）

---

## 6. 核心设计：TestSpec DSL（验收契约）

### 6.1 DSL 设计原则

* **不绑定具体 App**：只表达目标、可观察断言与证据，不引用内部控件 ID
* **可机器消费**：结构固定，可 Schema 校验
* **可扩展**：支持未来加入 verifiable（日志/接口/埋点）断言
* **默认安全**：强制 guards，避免误操作

### 6.2 TestSpec 字段定义（v0.1）

> 输出格式为 YAML；内部用 Pydantic/JSON Schema 强校验。

**必填**

* `version`：DSL 版本
* `id`：全局唯一
* `title`：用例标题
* `source[]`：文档引用（doc_id + loc）
* `goal`：用户目标与成功态
* `assertions.ui[]`：至少 1 条 UI 断言
* `guards.forbidden[]`：至少包含默认危险集合
* `budget`：max_steps/timeout/retries
* `evidence.required[]`：至少包含 screenshot_final 与 screenshot_on_assertions

**可选**

* `preconditions`：登录态/网络/地区/权限等
* `steps[]`：明确步骤（若文档有）
* `assertions.verifiable[]`：增强断言（默认 must=false）
* `tags[]`、`notes{}`

### 6.3 断言类型库（v1.0 先支持 UI 断言）

* `ui_text_present`：页面出现文本（contains/equals/regex）
* `ui_text_absent`：页面不应出现文本
* `ui_toast_present`：出现 Toast/提示条
* `ui_screen_landmark`：页面地标（标题栏/Tab/组合特征）
* `ui_element_state`：按钮禁用/启用、选中态（通过视觉/文案描述）
* `ui_count`：列表项数量变化（如新增一条）

> verifiable 断言类型（保留接口）：`logcat_contains`、`http_api`、`backend_state`、`analytics_event`

### 6.4 证据类型库（v1.0）

required：

* `screenshot_final`
* `screenshot_on_assertions`

optional：

* `screenshot_each_step`
* `logcat_tail`（window_sec）
* `ui_tree_dump`（预留）
* `screen_recording`（预留）

---

## 7. 系统闭环：Doc → TestSpec 编译流水线

### 7.1 流程总览

1. **Normalize（标准化）**
   输入文档 → 标准结构：doc_id、sections、paragraphs（带 loc）
2. **Requirement Mining（需求挖掘）**
   从段落中提取可测试声明 → RequirementItem[]
3. **Spec Synthesis（规格合成）**
   RequirementItem → 1..N 条 TestSpec（拆分主流程/异常/边界）
4. **Lint + AutoFix（强制合规）**
   补齐 guards/evidence/budget，阻断不可判定规格
5. **Export（落盘导出）**
   输出 YAML + index.json（追溯映射）

### 7.2 RequirementItem 中间结构（内部用，不对外）

字段：

* req_title
* user_goal
* success_ui[]（尽量具体可见）
* explicit_steps[]（若文档明确写了）
* preconditions（可空）
* verifiable_signals[]（可空）
* exceptions[]（可空）
* danger_ops[]（可空）
* source_loc（必须）

---

## 8. LLM 设计：两段式编译（稳定性关键）

### 8.1 设计原因

直接让模型“读文档并输出 TestSpec”容易出现：

* 输出混入解释文字
* 断言缺失或太抽象
* 步骤与成功态不对应

因此采用“两段式”：

* **A：抽事实（RequirementItem）**：严格 JSON，禁止脑补
* **B：合成规格（TestSpec YAML）**：把 success_ui 映射为 assertions，把 danger_ops 映射为 guards，补齐 budget/evidence

### 8.2 输出约束

* A 阶段必须输出 JSON 数组；解析失败则重试/降级
* B 阶段必须只输出 YAML；解析失败则重试/裁剪提取

### 8.3 温度与策略

* `temperature=0~0.2`（稳定优先）
* `max_tokens` 保证覆盖（文档长时需 chunk）
* 失败重试策略：同 prompt 1 次 + “仅输出格式”提示 1 次

---

## 9. Lint 与 AutoFix（防止假通过）

### 9.1 必须拦截（Error）

* `assertions.ui` 为空
* `budget.max_steps<=0` 或 `timeout_sec<=0`
* YAML/JSON 无法解析或 Schema 校验失败

### 9.2 自动修复（Fix）

* evidence.required 缺 `screenshot_final` → 自动添加
* evidence.required 缺 `screenshot_on_assertions` → 自动添加
* guards.forbidden 为空 → 注入默认危险集合：

  * real_payment / account_deletion / unbind_bankcard / send_message / submit_sensitive_form
* budget 缺失 → 默认 max_steps=40 timeout=180 retries=2

### 9.3 警告（Warn）

* 断言 target 过抽象（“成功/完成/已提交”等泛词）
* goal 过大（如“浏览应用/体验流程”）
* steps 为空且 assertions 太弱（只有 1 条泛文本）

---

## 10. 产品形态与交互

### 10.1 CLI 命令

* `doc2spec compile <input>`

  * input：文件或目录
  * 输出：out/specs/*.yaml + out/index.json
* `doc2spec lint <spec>`

  * 对已有 spec 做校验并输出问题
* `doc2spec export-json <spec_dir>`

  * YAML 批量转 JSON（可选）

### 10.2 输出目录规范

* `out/specs/{spec_id}.yaml`
* `out/index.json` 内容：

  * spec_id/title/source[]（用于追溯矩阵）

---

## 11. 技术方案（工程实现）

### 11.1 技术栈

* Python 3.10+
* Pydantic（Schema 校验）
* PyYAML（序列化）
* Typer/Rich（CLI）
* LLM Adapter：可接智谱/本地/企业网关（接口统一）

### 11.2 模块划分

* normalize：解析 txt/md → paragraphs（loc）
* mine：LLM 抽 RequirementItem
* synth：LLM 合成 TestSpec
* lint：校验与自动修复
* export：落盘 + index

### 11.3 LLM Adapter 接口（必须实现）

* `complete(prompt: str, input_text: str) -> str`

---

## 12. 数据结构与 Schema

### 12.1 JSON Schema 交付

* 提供 `tests/schema/testspec_v0.1.json`
* CLI 在导出前必须跑 Schema 校验

### 12.2 Spec ID 生成规则

* 默认：`{doc_id}-TS-{nnn}`
* 若文档中已有需求编号（如 PRD-LOGIN-001），优先沿用

---

## 13. 测试与验收

### 13.1 功能验收用例（平台自身）

* 输入一段包含“成功态文案”的 PRD，输出至少 1 条 TestSpec，且包含：

  * assertions.ui >= 1
  * evidence.required 含 final + on_assertions
  * guards.forbidden 非空
  * source.loc 不为空
* 输入 release note（新增/修复），输出“回归验证” TestSpec
* 输入接口错误码说明，生成 verifiable（must=false）断言不报错

### 13.2 Golden Test（关键）

* 固化 5~10 份代表性文档输入
* 固化对应输出 spec（golden YAML）
* 每次改 prompt/逻辑跑 diff（防回归）

---

## 14. 里程碑计划（按可交付拆分）

### M0（1~2 天）：最小闭环

* CLI compile
* Dummy LLM（先跑通框架）
* TestSpec 模型 + YAML 导出
* Lint + AutoFix

### M1（3~5 天）：接入真实 LLM

* 智谱/本地模型 Adapter
* 两段式 Prompt 稳定化
* Golden tests 通过

### M2（1 周）：输入增强与可用性

* 支持目录输入、多文件合并 index
* normalize 支持 Markdown 标题 loc
* 输出统计：生成数量、警告数量、失败原因聚类

---

## 15. 风险与对策

* **R：文档本身缺少可见成功态** → 生成的断言会弱
  对策：Lint 警告 + 建议补充“可见验收点”；后续引入页面地标库（第 3 层增强）
* **R：模型输出不稳定（夹带解释/格式错误）**
  对策：两段式 + 解析裁剪 + 重试 + temperature 低
* **R：过度生成（用例爆炸）**
  对策：提供粒度参数（只生成主流程/生成异常/生成边界）v1.1
* **R：安全风险（生成步骤包含危险操作）**
  对策：默认 guards + 严格 safety_mode；后续执行层强制拦截

---

## 16. 交付清单

1. CLI 工具：`doc2spec`
2. TestSpec DSL v0.1（Pydantic + JSON Schema）
3. 两段式 prompt 模板（可配置）
4. Lint+AutoFix 规则（含默认 guards/evidence/budget）
5. Golden Test 目录（输入文档 + 预期 spec）
6. 输出目录规范与 index.json（追溯映射）

---

## 17. 附录：TestSpec 示例（最小合规）

```yaml
version: "0.1"
id: "PRD_v1.md-TS-001"
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
    region: "any"
  app:
    install_state: "installed"
    cold_start: true
steps: []
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
    - "unbind_bankcard"
    - "send_message"
    - "submit_sensitive_form"
  safety_mode: "strict"
budget:
  max_steps: 40
  timeout_sec: 180
  retries:
    max_attempts: 2
    retry_on: ["timeout","blocked_by_popup"]
    backoff_sec: 3
evidence:
  required:
    - type: "screenshot_final"
    - type: "screenshot_on_assertions"
  optional: []
tags: ["p0","auth"]
notes: {}
```

