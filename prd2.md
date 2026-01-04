下面给你一份**第 2 层 PRD（TestSpec → PhoneAgent 指令编译）**，按“技术一看就知道怎么做”的粒度写，包含：目标、输入输出契约、编译产物、系统设计、关键算法、接口、验收标准、风险与边界，能直接开工。

---

## PRD：TestSpec → PhoneAgent 指令编译器（T2P Compiler）

### 1. 背景与问题

你第 1 层把各种文档（PRD/联调/错误码/release note…）统一变成了 **TestSpec DSL**：它描述目标、前置、断言、证据、预算、禁止操作等，但它还不是“可控的手机智能体任务”。

第 2 层要解决的问题是：
把 TestSpec **编译成 Open-AutoGLM / PhoneAgent 可执行、可控、可审计**的任务包（Task Bundle），并把断言编译成“观察任务”，为后续判定引擎提供结构化证据。

PhoneAgent 能执行的动作集合是固定的（Launch/Tap/Type/Swipe/Back/Home/Wait/Take_over，且还支持 Long Press / Double Tap 等）。([Z.AI][1])
它也支持**敏感操作确认回调**与**人工接管回调**（confirmation_callback / takeover_callback），非常适合把 Guards 和 Take_over 做成硬机制。([GitHub][2])

---

### 2. 目标（Goals）与非目标（Non-goals）

#### 2.1 Goals（必须做到）

1. **通用**：不绑定任何 App / 业务，只依赖 TestSpec。
2. **可控**：把 Guards、Budget、Evidence、Take_over 变成“硬约束 + 软策略”。
3. **可审计**：输出结构化的任务包，能够复现本次执行所用 prompt、预算、观察点、禁区策略。
4. **可判定**：把 Assertions 编成 ObservationSpec（观察任务），保证“证据结构化”，避免“看起来像成功”。

#### 2.2 Non-goals（这一层不做）

* 不做 Doc→TestSpec（那是第 1 层）
* 不做最终 Pass/Fail 判定（那是第 3 层 Judge）
* 不训练/微调模型，只做 prompt 与任务编译、策略注入

---

### 3. 用户与使用场景

#### 3.1 目标用户

* QA / 自动化测试工程师：把规格编译成可运行任务包
* 开发/测试平台工程师：把任务包喂给 Runner 执行并采集证据
* 产品/项目经理：以 TestSpec 为验收契约，保证“可测试”

#### 3.2 典型场景

* 用 release note 生成回归用例 → TestSpec → 编译成多机并行的手机任务包
* 用接口错误码说明生成异常路径用例 → 编译时强制 Guards，避免误触支付/删号
* 联调文档没有明确步骤 → Steps 留空，编译器生成“测试员模式”prompt，让 agent 自己规划但必须对齐断言

---

### 4. 输入/输出契约

#### 4.1 输入：TestSpec（来自第 1 层）

建议以 JSON/YAML 表示（示例结构）：

```yaml
id: TC_login_001
goal: "用户使用手机号+验证码登录成功"
preconditions:
  - "已安装目标App"
  - "网络可用"
  - "地区=CN"
steps: []  # 文档未给明确步骤则为空
assertions:
  ui:
    - id: A1
      type: "screen_contains_text"
      expect: "我的"
    - id: A2
      type: "element_visible"
      selector: {text: "退出登录"}
guards:
  - "禁止支付"
  - "禁止解绑银行卡"
  - "禁止发送消息"
budget:
  max_steps: 35
  timeout_sec: 180
  retry:
    max_attempts: 2
    backoff_sec: 3
evidence:
  - "screenshot_each_step"
  - "screenshot_on_assertions"
  - "final_screen"
  - "logcat_snippet_on_fail"
```

#### 4.2 输出：Task Bundle（编译产物）

**一个 TestSpec → 一个 Task Bundle 目录**（或一个 JSON 包），至少包含：

1. `task.json`（Runner 读取的统一任务描述）
2. `system_prompt.txt`（测试员模式系统提示词，含策略注入）
3. `user_task_prompt.txt`（面向 agent 的任务提示词：目标/前置/断言/步骤/禁区/预算）
4. `observation_spec.json`（断言→观察任务编译结果，给后续 Judge）
5. `policy.json`（Guards/Take_over/重试/超时/证据采集策略）
6. `compile_report.json`（编译诊断：缺失字段、风险提示、降级策略记录）

---

### 5. 核心设计：编译器做的两件事

> 你前面说得很准：
> (1) 生成“测试员式”的 system prompt / task prompt
> (2) 把 Assertions 编成“观察任务”

#### 5.1 生成“测试员模式”Prompt（Prompt Weaving）

**输入**：TestSpec + 基础 system prompt（cn/en）
Open-AutoGLM 支持用 `--lang` 切换中英文 prompt，并有配置文件路径（`phone_agent/config/prompts_zh.py` / `prompts_en.py`）可改。([GitHub][3])
另外也可在运行时通过 AgentConfig 传 `system_prompt` 覆盖。([GitHub][2])

**输出**：`system_prompt = base_prompt + TestModePatch`

TestModePatch（必须包含的策略块）：

1. **步步自检**：每一步执行前/后都要回答：是否更接近断言？如果不是，必须解释并回退/等待。
2. **不确定就保守**：识别不清/界面没加载 → `Wait`；走错路径 → `Back`；禁止“瞎点探索”。
3. **Guards 强约束**：任何可能触发 Guards 的行为，一律：

   * 触发确认回调（confirmation_callback）或直接停止并输出“需要人工确认/已停止”
     PhoneAgent 构造器支持 confirmation_callback 注入。([GitHub][2])
4. **Take_over 硬规则**：遇到验证码/登录/二次验证/生物识别 → 必须输出 `Take_over`，并等待人工接管回调（takeover_callback）。([Z.AI][1])
5. **预算纪律**：接近 max_steps/timeout 时要主动收敛，优先完成“最核心断言”，必要时 Fail fast。

> 备注：动作集合与 Take_over 是模型“输出动作”的一部分（Output Modality = Task Action）。([Z.AI][1])
> 编译器不改动作集合，只改“如何在动作集合里像测试员一样做事”。

#### 5.2 把 Assertions 编成 ObservationSpec（观察任务编译）

TestSpec 里的 Assertions 是“人类描述”，Judge 需要“结构化证据”。这一层要把它们变成 ObservationSpec：

ObservationSpec（示例）：

```json
{
  "checkpoints": [
    {"id":"CP0","when":"start","capture":["screenshot","current_app"]},
    {"id":"CP_STEP","when":"each_step","capture":["screenshot"]},
    {"id":"CP_A1","when":"on_candidate_success","capture":["screenshot"],"assert_refs":["A1","A2"]},
    {"id":"CP_FINAL","when":"finish","capture":["final_screen","screenshot_series_digest"]}
  ],
  "assertions_compiled": [
    {"id":"A1","type":"ocr_text_contains","value":"我的","evidence_key":"CP_A1.screenshot"},
    {"id":"A2","type":"ui_visual_element","selector":{"text":"退出登录"},"evidence_key":"CP_A1.screenshot"}
  ]
}
```

关键点：

* **断言要能被证据引用**：每个断言必须指向某个 checkpoint 的证据 key。
* **证据采集策略来自 Evidence 字段**：比如 `screenshot_each_step` → Runner 每步落盘；`logcat_snippet_on_fail` → Runner 在 fail 时抓取。
* 你现在用的是视觉智能体路线，所以默认断言编译以“截图证据”为主（OCR/视觉元素/版面变化），后续可扩展到 logcat/接口抓包（那通常是 Runner 插件能力）。

---

### 6. 系统架构与模块拆分

#### 6.1 组件图（逻辑）

TestSpec → **T2P Compiler** → Task Bundle → Runner(第3层) → Evidence → Judge(第3层)

#### 6.2 T2P Compiler 模块

1. **Parser/Normalizer**

   * 校验 TestSpec schema
   * 规范化：补默认 budget、标准化 guards 枚举、断言类型映射
2. **PromptFactory**

   * 读取基础 prompt（cn/en）([GitHub][3])
   * 注入 TestModePatch（策略块）
3. **GuardWeaver**

   * Guards → 风险动作词典/触发规则（例如：含“支付/下单/解绑银行卡/删除账号/发送/发布”）
   * 输出：policy.json + prompt 禁区说明
4. **TakeoverPlanner**

   * 根据 Preconditions/Steps/Assertions 推断“高概率接管点”（登录/验证码/2FA）
5. **BudgetMapper**

   * Budget.max_steps → AgentConfig.max_steps（PhoneAgent 支持）([GitHub][2])
   * 其它 timeout/retry 输出到 policy.json（Runner 执行）
6. **ObservationCompiler**

   * Assertions + Evidence → ObservationSpec
7. **Packager**

   * 输出 Task Bundle（含 compile_report）

---

### 7. 对接 Open-AutoGLM / PhoneAgent 的运行契约

虽然 Runner 是第 3 层，但这一层必须定义**可执行契约**，否则编译产物没法落地。

#### 7.1 最小运行方式（示例）

Z.ai 文档给了 `python main.py --base-url ... --model ... --apikey ... "Open Chrome browser"` 这种启动方式。([Z.AI][1])
同时 PhoneAgent 在代码层面支持 `ModelConfig(base_url=...)` 和 `AgentConfig(max_steps/lang/system_prompt)` 这些配置注入。([GitHub][2])

**本 PRD 规定 Runner 必须支持两种执行入口：**

* CLI 执行：`runner run <task_bundle_dir>`
* Python API：`run_task(bundle)`

#### 7.2 回调契约（Guards/Take_over）

* `confirmation_callback(reason: str) -> bool`

  * 返回 false：立即停止并产出 fail（或 blocked）
* `takeover_callback(reason: str) -> None`

  * Runner 进入人工模式：等待用户完成登录/验证码后继续

这两个回调是 PhoneAgent 原生支持的“注入点”。([GitHub][2])

---

### 8. 功能需求（Functional Requirements）

用 FR 编号方便拆任务：

**FR-01 TestSpec 解析与校验**

* 缺字段处理：goal/assertions/budget 缺失 → compile_report 标红并拒绝编译或降级策略（可配置）
* steps 为空允许（agent 自规划）

**FR-02 Prompt 编译**

* 支持 cn/en（继承 `--lang` / prompts 文件）([GitHub][3])
* 输出 system_prompt.txt / user_task_prompt.txt
* user_task_prompt 必须包含：Goal、Preconditions、Steps（若有）、Assertions、Guards、Budget、Evidence

**FR-03 Guards 编译**

* Guards → policy.json（结构化枚举）
* Guards → prompt 禁止说明（自然语言 + 清单）
* Guards → 运行时确认策略（绑定 confirmation_callback）

**FR-04 Take_over 编译**

* 规则库：验证码/登录/2FA/生物识别等关键词 + UI 迹象
* prompt 明确：识别到上述情形必须 `Take_over`([Z.AI][1])

**FR-05 Budget 编译**

* max_steps 写入 AgentConfig（max_steps 字段）([GitHub][2])
* timeout/retry 写入 policy.json（Runner 使用）

**FR-06 ObservationSpec 编译**

* Assertions → 原子断言（可机器判定）
* Evidence → checkpoints
* 每个断言必须有 evidence_key
* 支持至少三类断言：

  1. 文本包含（OCR）
  2. 视觉元素存在（按钮/标签）
  3. 页面状态（如“已登录”可用组合断言表达）

**FR-07 Task Bundle 打包**

* 目录结构固定
* compile_report 输出：风险点、降级记录、推断的 takeover 点

---

### 9. 非功能需求（NFR）

1. **确定性**：同一 TestSpec + 同一编译器版本 → 产物一致（除了生成时间戳）
2. **可追溯**：Task Bundle 内必须包含编译器版本、输入哈希、基础 prompt 版本
3. **安全默认**：默认开启 Guards 严格模式（有风险就拦）
4. **可扩展**：后续增加“日志/接口证据插件”不破坏 schema

---

### 10. 验收标准（Acceptance Criteria）

给你一套“能自动验收”的 AC：

1. **AC-01**：输入 steps 为空的 TestSpec，编译成功，产出 task bundle，prompt 中明确“允许 agent 自规划但必须对齐断言”。
2. **AC-02**：包含 Guards=“禁止支付”的用例，prompt 中出现禁区；policy.json 中存在对应 guard；Runner 注入 confirmation_callback 后，模拟触发风险动作时能阻止继续。
3. **AC-03**：包含“验证码/登录”的用例，prompt 明确要求 Take_over；ObservationSpec 含 takeover checkpoint；当 agent 输出 Take_over 时能触发 takeover_callback（可用桩函数验收）。([Z.AI][1])
4. **AC-04**：Budget.max_steps=10 时，AgentConfig.max_steps 被写入产物，且 runner 读取后强制最多 10 步。([GitHub][2])
5. **AC-05**：每条 assertion 在 ObservationSpec 中都能找到 evidence_key，且 checkpoints 能覆盖 `final_screen`。

---

### 11. 里程碑（建议拆两周可跑通）

* M1（2-3 天）：TestSpec schema + Packager + compile_report
* M2（2-3 天）：PromptFactory（cn/en）+ TestModePatch 注入（不改基础格式）
* M3（2-3 天）：GuardWeaver + policy.json + confirmation_callback 对接契约
* M4（2-3 天）：ObservationCompiler（截图证据为主）
* M5（2-3 天）：端到端 Demo：1 个用例能编译→Runner 执行→产证据包→（第3层 Judge 先用人工脚本判定）

---

### 12. 风险与对策（真实世界会搞事）

1. **模型“自信胡点”**：
   对策：Prompt 强制“非确定就 Wait/Back”，并把“每步自检”写成必须输出的检查项（让它不好意思乱来）。
2. **Guards 覆盖不全**：
   对策：双层防线——prompt 软约束 + confirmation_callback 硬拦截（回调是系统级）。([GitHub][2])
3. **断言过于主观**：
   对策：ObservationCompiler 强制结构化；无法结构化的断言编译时报 warning 并要求补充 Evidence/断言类型。
4. **验证码/登录不可自动化**：
   对策：Take_over 标准化成强制动作，并把接管点写入 policy 便于 Runner UI 做引导。([Z.AI][1])

---

