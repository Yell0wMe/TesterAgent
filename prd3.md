下面是**第 3 层 PRD（Runner + Judge + Report）**：把第 2 层编译出来的 Task Bundle 真正跑起来，产出**可复现证据链**，并给出**严格可解释的 Pass/Fail**。这一层是“自动化测试平台”的心脏。

（我会严格对齐 Open-AutoGLM 的能力边界：动作集合、verbose 轨迹、AgentConfig/max_steps、ADB/HDC 多设备、确认/接管回调、以及它的代码结构里已有截图/输入/设备控制模块等。([GitHub][1])）

---

# PRD：第 3 层 Run → Judge → Report（执行、判定、报告闭环）

版本：v1.0
范围：手机端 E2E（端到端）自动化测试运行与判定框架
输入：第 2 层产物 Task Bundle（含 prompts / policy / observation_spec）
输出：RunResult（含 Pass/Fail/Blocked + 证据包 + 报告）

---

## 1. 背景与要解决的问题

第 2 层已经把 TestSpec 编译为可控任务：

* 有测试员式 prompt（要求自检、保守、守规矩）
* 有 guards/takeover/budget 策略
* 有 ObservationSpec（断言与证据采集计划）

但如果没有第 3 层，你会遇到三大噩梦：

1. **执行不可控**：并发跑、超时、重试、设备断连、弹窗干扰、验证码接管……全靠人盯着。
2. **判定不可信**：Agent 自己说“任务完成✅”不算数（verbose 只是过程展示）。([GitHub][1])
3. **失败不可复盘**：没有结构化证据包（截图/步骤/日志），无法定位、无法回归、无法统计 flaky。

Open-AutoGLM 已提供关键能力与接口：动作集合、AgentConfig、verbose 输出、确认/接管回调、多设备管理与 ADB/HDC 连接等。([GitHub][1])
第 3 层就是把这些拼成一个“测试运行时”。

---

## 2. 目标与非目标

### 2.1 Goals（必须达成）

* **G1 闭环**：Task Bundle → 执行 → 采证 → 判定 → 报告，一条龙。
* **G2 可控**：超时、步数上限、重试、设备选择、接管等待都由系统控制（不是靠人盯）。
* **G3 可审计**：每个用例一次运行必须产出“证据链”与“可复现脚本”。
* **G4 可扩展**：Judge 支持插件式断言（OCR/VLM/UI 树/日志），Runner 支持插件式证据源（截图、录屏、logcat 等）。

### 2.2 Non-goals（v1.0 不做）

* 不做 Doc→TestSpec（第 1 层）
* 不做 TestSpec→TaskBundle（第 2 层）
* 不做“全自动绕过验证码/风控”（必须走 Take_over）
* 不做 GUI 后台（先 CLI + 结构化产物，后续再 UI）

---

## 3. 术语与产物定义

### 3.1 输入：Task Bundle（来自第 2 层）

目录/包内至少包含：

* `task.json`：运行参数（device_id/device_type/base_url/model/lang 等）
* `system_prompt.txt`、`user_task_prompt.txt`
* `policy.json`：guards、takeover、retry、timeout、evidence 策略
* `observation_spec.json`：断言编译结果、checkpoints、证据引用关系
* `compile_report.json`：编译诊断信息

> device_type 必须支持 `adb` / `hdc`，Open-AutoGLM 明确支持 Android ADB 与鸿蒙 HDC，并支持 `--device-type hdc`、`--device-id` 等方式指定。([GitHub][1])

### 3.2 输出：Run Artifact（一次运行的完整证据包）

固定目录结构（强约束，便于 CI/平台消费）：

```
runs/{run_id}/
  meta.json                 # 任务/设备/模型/版本/时间戳/输入哈希
  steps.jsonl               # 每一步结构化记录（动作/截图引用/耗时/状态）
  agent_verbose.log         # 原样保存 verbose（可选）
  evidence/
    screenshots/
      step_000.png
      step_001.png
      ...
      final.png
    logs/
      logcat_tail.txt       # 可选：失败时抓
    ui/
      uiauto_dump.xml       # 可选：如果启用 UI 树
  judge/
    verdict.json            # Pass/Fail/Blocked + 断言逐条解释
  report/
    report.html             # 可选：人类友好
    report.json             # 结构化汇总
  repro/
    actions.json            # 可回放动作序列（带脱敏）
```

---

## 4. 总体架构

```
Task Bundle
   │
   ▼
Runner（执行与采证）
   │ 产出证据包（screenshots/logs/steps）
   ▼
Judge（断言判定）
   │ 产出 verdict.json（可解释）
   ▼
Reporter（汇总/趋势/失败聚类）
```

Runner 核心依赖 Open-AutoGLM/PhoneAgent 的：

* 动作空间（Launch/Tap/Type/Swipe/Back/Home/Wait/Take_over 等）([GitHub][1])
* AgentConfig（max_steps、lang、verbose 等）([GitHub][1])
* confirmation_callback / takeover_callback（敏感操作确认与人工接管）([GitHub][1])
* 多设备与远程连接（adb connect、hdc tconn、--device-id、--list-devices 等）([GitHub][1])
* 工程结构里已有截图/输入/设备控制模块（`phone_agent/adb/screenshot.py`, `phone_agent/adb/input.py`, `phone_agent/adb/device.py` 等），利于做 step hook。([GitHub][1])

---

## 5. Runner：执行与采证（核心）

### 5.1 Runner 的职责

* 读取 Task Bundle，准备 AgentConfig/ModelConfig（base_url/model/api_key/temperature…）与设备连接
* 执行任务：调用 PhoneAgent（Python API 或 CLI）
* 在执行过程中按 ObservationSpec 采集证据（截图为核心）
* 处理异常：超时、断连、卡死、弹窗干扰、Take_over 等
* 输出 steps.jsonl + 证据文件 + meta.json

Open-AutoGLM 提供 Python API 与配置对象（ModelConfig/AgentConfig）示例，且支持 verbose 输出每步“思考+动作”。([GitHub][1])

### 5.2 执行模式（v1.0）

* **单用例单设备**：`runner run runspec_dir --device-id xxx`
* **批量多设备**：`runner batch task_bundles/ --device-pool pool.json --parallel 4`
* **CI 模式**：输出 JUnit XML/JSON（便于集成）

### 5.3 关键机制

#### 5.3.1 步数与超时

* `budget.max_steps` → 写入 AgentConfig.max_steps（PhoneAgent 支持）([GitHub][1])
* `budget.timeout_sec`：Runner 外层计时器（超时强制终止，标记为 `Fail:timeout`）
* 终止时必须截 final screenshot（即使失败）

#### 5.3.2 Guard 强制（双层防线）

* 软：prompt 里列出禁止操作（第 2 层已做）
* 硬：confirmation_callback 拦截敏感操作，用户拒绝则立即停止并判定为 `Blocked:guard_denied` 或 `Fail:guard_violation`（策略可配）([GitHub][1])

#### 5.3.3 Take_over（人工接管）

* 触发条件：agent 输出 `Take_over`（动作集合原生支持）([GitHub][1])
* 执行方式：Runner 通过 takeover_callback 进入等待，提示操作者完成验证码/登录/2FA；完成后继续。([GitHub][1])
* 计时策略：

  * v1.0 默认 takeover 时间计入 timeout（简单），并在 meta 里记录 takeover_duration
  * v1.1 可配置“takeover 不计入 timeout，但计入 wall time”

#### 5.3.4 证据采集（Evidence）

Runner 必须实现至少两种采集策略：

* `screenshot_each_step`：每步动作前后（或后）截图
* `screenshot_final`：结束必截
  此外，ObservationSpec 里定义的 checkpoints（on_assertions/on_candidate_success）要额外截屏并打标签。

> Open-AutoGLM 本身就有 adb 截图模块与设备控制模块，Runner 可以复用它们或在 action handler 周围打 hook。([GitHub][1])

#### 5.3.5 结构化步骤日志（steps.jsonl）

每一步写一行 JSON，示例：

```json
{"i":12,"ts":"2026-01-04T16:12:01+08:00","action":{"name":"Tap","args":{"x":500,"y":100}},"screen":"evidence/screenshots/step_012.png","status":"ok","latency_ms":842}
```

并记录：

* action 名称（来自 agent 输出，如 Launch/Tap/Type/Swipe…）([GitHub][1])
* 截图路径
* 步耗时、总耗时、重试次数
* 如触发 takeover/guard，写入事件行：`event: takeover_start / takeover_end / guard_prompt`

#### 5.3.6 重试与“flaky”识别（v1.0 简版）

* 只在指定错误码/异常类型触发重试（policy.json 的 retry_on）
* 每次重试必须生成新的 run_id，但在 report 汇总为同一个 case_id
* Judge 结果为 Pass，但至少一次失败 → 标记 `flaky_suspected=true`

---

## 6. Judge：断言判定（不信“AI 自己说完成”）

Open-AutoGLM 的 verbose 里会出现“✅ 任务完成”，但那只是 agent 自述，并非验收。([GitHub][1])
Judge 必须只信：ObservationSpec + Evidence。

### 6.1 Judge 输入输出

输入：

* `observation_spec.json`
* `evidence/`（截图序列、final、可选 logcat/ui dump）
* `steps.jsonl`（用于定位断言触发时刻）

输出：

* `judge/verdict.json`

### 6.2 Verdict 格式（强解释）

```json
{
  "case_id":"TC_login_001",
  "run_id":"20260104_161201_xxx",
  "status":"PASS",
  "summary":"A1/A2 均满足",
  "assertions":[
    {"id":"A1","must":true,"status":"PASS","evidence":".../step_018.png","why":"OCR 命中 '我的'"},
    {"id":"A2","must":true,"status":"PASS","evidence":".../step_018.png","why":"检测到 '退出登录' 按钮"}
  ],
  "meta":{
    "takeover_used":true,
    "guards_triggered":false,
    "duration_sec":73.4
  }
}
```

### 6.3 断言执行器（Assertion Engines）

v1.0 要求至少实现：

* **TextEngine（OCR/VLM）**：支持 `ui_text_present / absent`
* **LandmarkEngine**：页面地标（标题/Tab/组合特征），用于 `ui_screen_landmark / ui_route`
* **BasicStateEngine**：按钮/禁用态/选中态（通过视觉线索或文本线索）

实现形态：插件接口（后续可加 logcat、网络抓包、UI 树）

### 6.4 判定策略

* `must=true` 的断言全通过 → PASS
* 任一 `must=true` 失败 → FAIL
* 遇到 takeover 未完成 / guard 拒绝 / 设备断连 → BLOCKED（单独统计，避免污染质量）

---

## 7. Reporter：报告与趋势（给人看，也给 CI 看）

### 7.1 报告内容（v1.0）

* 每个用例：PASS/FAIL/BLOCKED、耗时、重试次数、是否 takeover、失败断言列表
* 失败聚类（规则版）：timeout / device_disconnect / assertion_failed / guard_denied / crash_suspected
* Top flaky 用例（过去 N 次里波动最大的）

### 7.2 输出格式

* `report/report.json`：结构化汇总（CI/平台接入）
* `report/report.html`：人类友好（可选）
* `junit.xml`：兼容传统 CI（可选）

---

## 8. 关键接口与契约（让第 1/2 层无痛对接）

### 8.1 Runner CLI

* `runner run <task_bundle_dir> --device-id <id> [--device-type adb|hdc]`
* `runner batch <task_bundle_root> --pool pool.json --parallel N`

### 8.2 Runner Python API

```python
result = run_task(bundle_dir, device_id="...", device_type="adb")
```

### 8.3 设备池配置（pool.json）

```json
{
  "devices":[
    {"id":"192.168.1.100:5555","type":"adb"},
    {"id":"192.168.1.101:5555","type":"hdc"}
  ]
}
```

Open-AutoGLM 已给出 adb connect / hdc tconn / device-id 指定与 list-devices 思路，Runner 复用即可。([GitHub][1])

---

## 9. 功能需求（FR）

**FR-01 Task Bundle 读取与校验**

* 缺关键文件 → 直接 BLOCKED（compile bug）

**FR-02 设备连接与健康检查**

* 支持 adb/hdc；启动前检查设备在线、屏幕可截图
* 断连 → 按 policy 重连一次，失败 BLOCKED:device_disconnect ([GitHub][1])

**FR-03 执行与步级采证**

* 支持 verbose（存档 agent_verbose.log）([GitHub][1])
* 每步至少截一张图（若配置 each_step）
* 必须产 final 截图

**FR-04 Take_over 处理**

* takeover_callback 进入等待、提示与继续机制 ([GitHub][1])

**FR-05 Guard 拦截**

* confirmation_callback 拦截敏感操作；拒绝后停止 ([GitHub][1])

**FR-06 Judge 判定**

* 逐条断言输出 PASS/FAIL + evidence 指向
* must=false 失败不影响整体 PASS，但要记录为 warning

**FR-07 报告生成**

* 输出 report.json，包含每个 case 的 verdict 与证据索引

**FR-08 可复现回放（v1.0 简版）**

* 记录 actions.json（坐标/文本脱敏）
* 后续可用“脚本回放器”复现（v1.1）

---

## 10. 非功能需求（NFR）

* **确定性**：同一证据包，Judge 判定必须稳定
* **可观测性**：所有 run 产出 meta.json（模型/温度/max_steps/lang/device 等），环境变量也要落盘（Open-AutoGLM 支持通过环境变量配置 base_url/model/api_key/max_steps/device_id/device_type/lang 等）([GitHub][1])
* **安全**：steps/action 记录必须脱敏（验证码、密码、手机号等）
* **可并发**：批量执行时同一设备不并发；多设备并发可配置 N

---

## 11. 验收标准（AC，能自动验收）

* **AC-01**：对一个包含 `max_steps=10` 的 bundle，Runner 实际不超过 10 步，并产出 steps.jsonl + final.png。([GitHub][1])
* **AC-02**：触发 `Take_over` 时，Runner 进入等待，操作者回车后继续，并在 meta 记录 takeover_duration。([GitHub][1])
* **AC-03**：触发 guard（例如“删除账号”），confirmation_callback 返回否，Runner 终止并产出 BLOCKED/FAIL（按 policy），并保留最后截图与原因。([GitHub][1])
* **AC-04**：Judge 对至少 2 条 ui_text_present 断言给出逐条 evidence 指向，且 verdict.json 可解释。
* **AC-05**：批量模式下，多设备并行执行，report.json 汇总每条用例的状态与耗时。

---

## 12. 里程碑建议（按“先跑通再变强”）

* **M0（1–2 天）**：Runner 单用例跑通（截图+steps.jsonl+final）
* **M1（2–3 天）**：接入 callbacks（takeover/confirmation）+ 超时/重试
* **M2（3–5 天）**：Judge v1（OCR/VLM 文本断言 + verdict.json）
* **M3（2–3 天）**：Reporter（json + html + flaky 初步）
* **M4（后续）**：回放器、UI 树断言、logcat 插件、网络抓包插件

---

## 13. 风险与对策（现实世界会整活）

* **UI 变化导致断言不稳**：优先地标断言（组合特征），必要时引入 UI 树插件（v1.1）
* **验证码/风控频繁**：把 BLOCKED 单独统计；用例库里标注 takeover_required
* **设备不稳定（WiFi ADB/HDC 掉线）**：重连策略 + pool 里备用机；Open-AutoGLM 已提供远程连接排障与 device-id 管理思路可复用 ([GitHub][1])
* **“AI 说完成”误导**：只信 Judge 的断言判定；verbose 只用于排障 ([GitHub][1])

---