

## 指令：停止写死操作，改为对接智谱 Open-AutoGLM PhoneAgent

### 目标

把当前系统改造成三层架构（对应三份 PRD）：

1. **第1层 Doc → TestSpec**：输出结构化测试规格（不含坐标/控件ID）
2. **第2层 TestSpec → AgentJob/TaskBundle**：编译出“测试员任务提示词 + 预算/guards/观察任务”
3. **第3层 Runner+Judge**：Runner 调用智谱开源 **PhoneAgent** 执行，采集证据；Judge 只依据断言+证据判定 Pass/Fail

> 禁止：在系统中硬编码“点击某坐标/固定步骤脚本”。所有操作由 PhoneAgent 基于屏幕自主规划执行；我们的系统只提供任务、约束、证据计划与判定。

---

## 一、引入 Open-AutoGLM（必须真实拉代码/安装依赖）

### 方案A：Git 子模块（推荐，便于固定版本）

在仓库根目录执行：

```bash
git submodule add https://github.com/zai-org/Open-AutoGLM.git vendor/open-autoglm
git submodule update --init --recursive
```

Python 侧用可编辑安装（在 CI/本地都需要）：

```bash
pip install -r vendor/open-autoglm/requirements.txt
pip install -e vendor/open-autoglm
```

### 方案B：直接依赖 Git URL（可选）

在 `requirements.txt` 加：

```
git+https://github.com/zai-org/Open-AutoGLM.git@<PINNED_COMMIT>
```

> 必须固定 commit，不要漂移。

---

## 二、定义“唯一正确”的交互接口（Adapter 层）

新增模块：`execution/phoneagent_adapter.py`
这个 Adapter 是**系统与 PhoneAgent 交互的唯一入口**。后续任何执行都必须走它。

### 2.1 统一输入结构：AgentJob（来自第2层编译产物）

新增数据结构（Pydantic/Dataclass 均可）：

```python
class AgentJob:
    job_id: str
    task_text: str               # 第2层编译出来的“测试员任务提示词”
    model:
        base_url: str
        model_name: str          # e.g. "autoglm-phone"
        api_key: str
    device:
        device_type: str         # "adb" or "hdc"
        device_id: str | None
    run:
        lang: str                # "zh" or "en"
        max_steps: int
        timeout_sec: int         # Runner外层控制
        verbose: bool
    policy:
        guards: list[str]        # forbidden list
        takeover_required_hints: list[str]  # 可选
    observation_spec: dict       # 第2层产物：断言->观察任务
    evidence_plan: dict          # 截图/日志等采集计划
    workspace_dir: str           # 本次运行产物目录
```

### 2.2 统一输出结构：AgentRunResult（给第3层 Judge 用）

```python
class AgentRunResult:
    job_id: str
    status: str                  # "finished" | "timeout" | "blocked" | "error"
    steps_jsonl_path: str
    screenshots_dir: str
    final_screenshot_path: str
    agent_verbose_log_path: str
    repro_actions_path: str
    meta_path: str
```

---

## 三、PhoneAgent 的两种调用方式（必须都支持，默认用 CLI）

### 3.1 默认：CLI 子进程（最稳，易落地）

在 `phoneagent_adapter.py` 实现：

* 组装命令：`python vendor/open-autoglm/main.py ... "<task_text>"`
* 必须支持参数注入：

  * `--base-url`
  * `--model`
  * `--apikey`
  * `--device-type`（adb/hdc）
  * `--device-id`（可选）
  * `--max-steps`
  * `--lang`
  * `--verbose`

> 运行时把 stdout/stderr 全量写入 `agent_verbose.log`，并解析其中的动作输出（如果无法稳定解析，则至少落盘日志和截图）。

示例命令拼接（仅示意）：

```python
cmd = [
  sys.executable, "vendor/open-autoglm/main.py",
  "--base-url", job.model.base_url,
  "--model", job.model.model_name,
  "--apikey", job.model.api_key,
  "--device-type", job.device.device_type,
  "--lang", job.run.lang,
  "--max-steps", str(job.run.max_steps),
]
if job.device.device_id:
  cmd += ["--device-id", job.device.device_id]
if job.run.verbose:
  cmd += ["--verbose"]
cmd += [job.task_text]
```

### 3.2 可选：Python API（后续增强用，先不阻塞）

仅当 CLI 路线跑通并且需要回调/单步 hook 时再启用。

---

## 四、必须实现的“证据采集”机制（Runner 负责，不依赖 Agent 自觉）

新增模块：`runner/runner_phoneagent.py`

Runner 工作流：

1. 创建 `runs/{run_id}/` 目录结构
2. 调用 `PhoneAgentAdapter.run(job)`
3. 在执行期间按 `evidence_plan` 采集证据（最小集合必须有）：

   * `screenshot_each_step`（若配置开启）
   * `screenshot_final`（必须）
   * `screenshot_on_assertions`（必须：在关键 checkpoint 额外抓）
4. 写 `steps.jsonl`：每步至少记录 `{step_index, action, screenshot_path, ts, latency}`
5. 写 `meta.json`：记录模型、设备、budget、输入哈希、PRD版本、git commit 等

> 关键：就算 PhoneAgent 自己有 verbose，你也必须在 Runner 侧落“结构化 steps.jsonl + 截图序列”。
> 之后 Judge 只读证据，不信 Agent 的“完成✅”。

---

## 五、Guards 与 Take_over：必须是“硬约束”，不是 prompt 里写一句

### 5.1 Guards（硬拦截）

在 Runner 实现双层拦截：

* **层1（软）**：第2层 prompt 已写“禁止操作清单”
* **层2（硬）**：Runner 解析每步 action/文本输入的意图（最简单：匹配关键词），一旦命中 guard，立刻终止并标记 `BLOCKED:guard_violation`

Guard 关键词最小集（可配置）：

* 支付/付款/下单/确认支付
* 删除账号/注销/解绑银行卡/解绑银行卡
* 发送/发布/转发/私信/短信

> 如果后续切 Python API 并接入 `confirmation_callback`，则把硬拦截升级成“可交互确认”；v1 先直接拦截终止。

### 5.2 Take_over（必须阻断）

当日志/动作表明进入验证码/登录/2FA（关键词或页面提示）：

* Runner 将状态标记为 `BLOCKED:takeover_required`
* 等待人工（如果你的系统支持交互），否则直接失败并输出证据包

> v1 可以不做“人工接管 UI”，但必须把这种情况正确分类，不要算 FAIL/Pass。

---

## 六、把第2层产物真正用起来（不要再写固定步骤）

修改第2层编译器输出，使其产出 `AgentJob` 或 TaskBundle 目录，包含：

* `task_text`（必须：测试员任务提示词）
* `policy.json`（guards、budget、retry、timeout）
* `observation_spec.json`（断言→观察任务）
* `evidence_plan.json`（截图/日志计划）

并且 Runner 只消费这些文件，不允许任何地方出现“硬编码点击流程”。

---

## 七、Judge：只根据断言+证据判定（从第3层 PRD 落地）

新增模块：`judge/judge_v1.py`

输入：

* `observation_spec.json`
* `runs/{run_id}/evidence/screenshots/*`
* `runs/{run_id}/steps.jsonl`

输出：

* `runs/{run_id}/judge/verdict.json`

v1 必须支持两类断言：

* `ui_text_present`：在 final 或指定 checkpoint 截图中能找到文本（OCR 可先用最简实现/外接）
* `ui_screen_landmark`：通过“标题/Tab/关键文本组合”判定页面到达（先规则版）

判定规则：

* 所有 `must=true` 断言通过 -> PASS
* 任一失败 -> FAIL
* `BLOCKED:*` -> BLOCKED（独立统计）

---

## 八、验收标准（你必须做到这些才算“对接成功”）

1. 项目中不再出现“硬编码步骤脚本执行 UI”的逻辑
2. 仓库中存在 `vendor/open-autoglm`（或等效依赖）且 CI 能安装/运行
3. Runner 能用一个最简单 `AgentJob` 调起 PhoneAgent，跑 10 步以内任务并产出：

   * steps.jsonl
   * screenshot 序列
   * final.png
   * agent_verbose.log
4. 任意一条 `ui_text_present` 断言能基于证据判定 Pass/Fail（即使 OCR 先用简版）
5. Guards 命中时能被硬拦截，结果为 BLOCKED，并保留最后证据

---

## 九、开发顺序（照这个做，别发散）

1. 引入 Open-AutoGLM（子模块/依赖固定）
2. 实现 `AgentJob` + `PhoneAgentAdapter`（先 CLI）
3. 实现 Runner：目录结构 + steps.jsonl + 截图 final
4. 接入第2层编译产物（task_text + policy + observation_spec + evidence_plan）
5. 实现 Judge v1（只做 2 种断言）
6. 再考虑 takeover 交互、confirmation_callback、UI 树、logcat 等增强

---

## 十、禁止事项（最重要）

* 不允许写任何“固定坐标点击脚本”来替代 PhoneAgent
* 不允许把测试流程写死在代码里（流程应该来自 TestSpec/TaskBundle）
* 不允许用 “Agent 说完成” 作为 Pass（必须 Judge 依据证据判定）

