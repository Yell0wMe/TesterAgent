<div align="center">

# 🤖 TesterAgent

**文档驱动的手机端自动化测试平台**

将自然语言 PRD/设计文档自动转换为结构化测试规格，编译为智能体可执行任务，并产出可解释的测试报告。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ 特性

- 🔄 **文档即用例** — 直接从 PRD/设计文档提取可测试需求
- 📋 **结构化输出** — 生成标准 TestSpec YAML，支持版本控制
- 🎯 **可执行规格** — 编译为 PhoneAgent 可执行的 Task Bundle
- 🛡️ **安全机制** — 内置 Guards 禁区 + Take_over 人工接管
- 📊 **可解释判定** — 不信"AI 说完成"，只信证据链判定
- 🔗 **完整追溯** — 每条断言都有证据，每个结果都可复现

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TesterAgent                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   PRD/文档    ──►   TestSpec    ──►   Task Bundle    ──►   Report          │
│                                                                             │
│   ┌─────────┐      ┌──────────┐      ┌─────────────┐      ┌───────────┐    │
│   │         │      │          │      │             │      │           │    │
│   │ doc2spec│ ──►  │   t2p    │ ──►  │   runner    │ ──►  │  verdict  │    │
│   │         │      │          │      │   + judge   │      │  + report │    │
│   │ 第1层   │      │  第2层   │      │    第3层    │      │           │    │
│   └─────────┘      └──────────┘      └─────────────┘      └───────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

| 层级 | 工具 | 输入 | 输出 |
|------|------|------|------|
| **第 1 层** | `doc2spec` | PRD/Markdown 文档 | TestSpec YAML |
| **第 2 层** | `t2p` | TestSpec YAML | Task Bundle |
| **第 3 层** | `runner` | Task Bundle | Evidence + Verdict + Report |

---

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/your-org/TesterAgent.git
cd TesterAgent

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e ".[dev,zhipu]"

# 配置 API Key（使用智谱 AI）
cp .env.example .env
# 编辑 .env 填入 ZHIPU_API_KEY
```

### 端到端示例

```bash
# 1️⃣ 文档 → TestSpec
doc2spec compile examples/sample_prd.md -o out/

# 2️⃣ TestSpec → Task Bundle
t2p compile out/specs/ -o bundles/

# 3️⃣ 执行 + 判定 + 报告
runner batch bundles/ --mock

# 查看报告
open runs/report/report.html
```

---

## 📦 第 1 层：Doc2Spec

**将自然语言文档转换为结构化 TestSpec。**

### 命令

```bash
# 编译文档（使用真实 LLM）
doc2spec compile your_prd.md -o out/

# 编译文档（Mock 模式，用于调试）
doc2spec compile your_prd.md --dummy -o out/

# 校验 TestSpec
doc2spec lint out/specs/

# 导出 JSON 格式
doc2spec export-json out/specs/
```

### 输出结构

```
out/
├── specs/
│   ├── PRD-TS-001.yaml    # 生成的 TestSpec
│   ├── PRD-TS-002.yaml
│   └── ...
└── index.json             # 追溯索引
```

### TestSpec 示例

```yaml
version: '0.1'
id: PRD-TS-001
title: 用户登录后进入首页

source:
  - doc_id: PRD_v1.md
    loc: 'H2: 用户登录 > P3'

goal:
  user_intent: 完成手机号+验证码登录
  success_state: 进入首页且显示用户信息

preconditions:
  account:
    state: logged_out
  device:
    network: wifi
  app:
    cold_start: true

assertions:
  ui:
    - id: A1
      type: ui_text_present
      target: 首页
      must: true
    - id: A2
      type: ui_text_present
      target: 我的
      must: true

guards:
  forbidden:
    - real_payment
    - account_deletion
  safety_mode: strict

budget:
  max_steps: 40
  timeout_sec: 180

evidence:
  required:
    - type: screenshot_final
    - type: screenshot_on_assertions
```

---

## 🔧 第 2 层：T2P Compiler

**将 TestSpec 编译为 PhoneAgent 可执行的 Task Bundle。**

### 命令

```bash
# 编译单个 TestSpec
t2p compile out/specs/PRD-TS-001.yaml -o bundles/

# 批量编译
t2p compile out/specs/ -o bundles/
```

### Task Bundle 结构

```
bundles/PRD-TS-001_bundle/
├── task.json              # 任务配置（AgentConfig）
├── system_prompt.txt      # 系统提示词（测试员模式）
├── user_task_prompt.txt   # 用户任务描述
├── policy.json            # 策略配置（Guards/Takeover/Retry）
├── observation_spec.json  # 观察任务规格（断言→证据映射）
└── compile_report.json    # 编译诊断报告
```

### 核心功能

| 模块 | 功能 |
|------|------|
| **PromptFactory** | 生成测试员模式 prompt（步步自检、保守策略） |
| **GuardWeaver** | 编译 Guards 禁区（支付/删号/解绑） |
| **TakeoverPlanner** | 规划人工接管点（验证码/登录/2FA） |
| **ObservationCompiler** | 编译断言为可判定的证据采集任务 |

---

## ▶️ 第 3 层：Runner + Judge + Report

**执行任务、采集证据、判定断言、生成报告。**

### 命令

```bash
# 执行单个任务
runner run bundles/PRD-TS-001_bundle/ --mock

# 批量执行
runner batch bundles/ --mock --parallel 2

# 单独判定
runner judge runs/20260104_xxx/

# 生成报告
runner report runs/ -o report/
```

### Run Artifact 结构

```
runs/{run_id}/
├── meta.json              # 运行元数据
├── steps.jsonl            # 步骤记录（每步一行 JSON）
├── evidence/
│   └── screenshots/
│       ├── step_000.png
│       ├── step_001.png
│       └── final.png
├── judge/
│   └── verdict.json       # 判定结果（可解释）
└── report/
    ├── report.json        # 结构化报告
    └── report.html        # 可视化报告
```

### Verdict 示例

```json
{
  "case_id": "PRD-TS-001",
  "run_id": "20260104_161201_xxx",
  "status": "PASS",
  "summary": "2 通过, 0 失败",
  "assertions": [
    {
      "id": "CA_001",
      "status": "PASS",
      "evidence": "evidence/screenshots/final.png",
      "why": "OCR 命中 '首页'"
    },
    {
      "id": "CA_002",
      "status": "PASS",
      "evidence": "evidence/screenshots/final.png",
      "why": "OCR 命中 '我的'"
    }
  ]
}
```

---

## ⚙️ 配置

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ZHIPU_API_KEY` | 智谱 AI API 密钥 | - |
| `DOC2SPEC_LLM_MODEL` | 模型名称 | `glm-4` |
| `DOC2SPEC_TEMPERATURE` | 温度参数 | `0.1` |
| `DOC2SPEC_MAX_TOKENS` | 最大 Token 数 | `4096` |
| `DOC2SPEC_OUTPUT_DIR` | 输出目录 | `out` |

### .env 配置

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
ZHIPU_API_KEY=your-api-key-here
DOC2SPEC_LLM_MODEL=glm-4
DOC2SPEC_TEMPERATURE=0.1
```

---

## 📁 项目结构

```
TesterAgent/
├── src/
│   ├── doc2spec/              # 第 1 层：Doc → TestSpec
│   │   ├── cli.py             # CLI 入口
│   │   ├── models/            # Pydantic 模型
│   │   ├── modules/           # 核心模块
│   │   │   ├── normalize.py   # 文档规范化
│   │   │   ├── mine.py        # 需求挖掘
│   │   │   ├── synth.py       # 规格合成
│   │   │   ├── lint.py        # 校验修复
│   │   │   └── export.py      # 导出
│   │   ├── adapters/          # LLM 适配器
│   │   └── prompts/           # Prompt 模板
│   │
│   ├── t2p/                   # 第 2 层：TestSpec → Task Bundle
│   │   ├── cli.py
│   │   ├── models/            # Bundle 模型
│   │   └── compiler/          # 编译器模块
│   │       ├── parser.py
│   │       ├── prompt_factory.py
│   │       ├── guard_weaver.py
│   │       ├── takeover.py
│   │       ├── observation.py
│   │       └── packager.py
│   │
│   └── runner/                # 第 3 层：执行 + 判定 + 报告
│       ├── cli.py
│       ├── models/            # Artifact/Verdict/Report 模型
│       ├── executor/          # 执行器
│       │   ├── runner.py
│       │   ├── device.py
│       │   ├── evidence.py
│       │   └── callbacks.py
│       ├── judge/             # 判定器
│       │   ├── judge.py
│       │   └── engines/
│       │       └── text.py    # OCR/文本引擎
│       └── reporter/          # 报告器
│
├── schemas/                   # JSON Schema
├── examples/                  # 示例文档
├── tests/                     # 测试用例
├── out/                       # TestSpec 输出
├── bundles/                   # Task Bundle 输出
└── runs/                      # 运行结果
```

---

## 🧪 开发

```bash
# 运行测试
pytest tests/ -v

# 代码格式化
black src/ tests/

# Lint 检查
ruff check src/

# 类型检查
mypy src/
```

---

## 🗺️ Roadmap

- [x] **v0.1** — 三层架构核心实现
- [ ] **v0.2** — 真实设备执行（ADB/HDC）
- [ ] **v0.3** — OCR/VLM 断言引擎
- [ ] **v0.4** — 回放器 + 可视化调试
- [ ] **v0.5** — CI/CD 集成（GitHub Actions/Jenkins）
- [ ] **v1.0** — 生产就绪

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE)

---

<div align="center">

**Built with ❤️ for QA Engineers**

</div>
