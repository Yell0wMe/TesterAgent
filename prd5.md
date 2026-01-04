# PRD：Web 测试控制台（设备选择｜上传PRD｜实时过程｜实时画面｜结果与证据）

版本：v1.0
目标用户：测试同学（QA）、测试负责人、研发（查看失败复盘）
依赖系统：你现有三层链路（Doc→TestSpec→PhoneAgent 编译→Runner/Judge/Report）

---

## 1. 背景与问题

目前系统已经能跑通“文档→规格→PhoneAgent 执行→证据→判定”，但对测试同学来说仍然“太工程化”：

* 不知道该选哪台机跑、机子状态如何
* PRD/联调文档怎么喂进去、是否已被解析成规格
* 运行过程中看不到实时进度，只能等结果
* 失败时缺少一眼可用的“证据/步骤/截图/日志”入口
* 想看实时手机画面（确认卡在哪、是否出现验证码/弹窗）很麻烦

因此需要一个 Web 控制台，把整个流程做成**可操作、可观察、可复盘**的闭环。

---

## 2. 产品目标与成功标准

### 2.1 目标（必须）

1. **一键发起测试**：选设备 + 上传文档 + 点开始
2. **实时可观察**：实时看到“解析/编译/执行/判定”状态与日志流
3. **实时画面**：能查看正在跑的设备屏幕（低延迟、可刷新）
4. **结果可复盘**：用例级结果、断言级判定、证据一键下载
5. **对测试友好**：无须理解底层 PhoneAgent/ADB/脚本

### 2.2 成功标准（上线两周）

* 80% 测试任务通过 UI 发起（不再依赖命令行）
* 单任务从创建到开始执行 < 2 分钟（不包含用例执行时间）
* 失败用例 90% 能在 UI 内完成复盘（不需要拉工程日志到本地）

---

## 3. 范围与非范围

### 3.1 v1.0 范围

* 设备池管理（Android ADB / Harmony HDC）：列出、占用、释放、健康状态
* 上传文档（PRD/评审纪要/联调文档）：支持 md/txt/docx/pdf（pdf 非扫描优先；扫描版可能降级）
* 创建测试任务：选择设备、运行参数、文档输入
* 实时进度：阶段状态、步骤流、日志流、错误提示
* 实时画面：运行中设备屏幕预览（轮询截图或推送帧）
* 结果查看：Pass/Fail/Blocked，断言逐条解释，证据浏览/下载
* 历史任务：可检索、可复跑（同文档、同配置）

### 3.2 v1.0 非范围（先不做）

* 多租户复杂权限体系（v1 只做简单登录/角色）
* 大规模分布式调度与弹性扩缩（v1 单集群/单机房）
* 在网页上“远程控制手机操作”（先只看，不做点按控制，避免误操作）
* 复杂 RAG 知识库（文档解析先走你现有链路）

---

## 4. 用户画像与核心场景

### 4.1 用户

* QA 执行者：上传文档，选设备，盯过程，导出报告
* QA 负责人：看测试覆盖与失败趋势
* 研发：定位失败原因、对照证据

### 4.2 核心场景

1. **冒烟测试**：刚发版，跑“打开微信/登录/首页”等基础用例
2. **回归测试**：上传 release note 或 PRD 章节，生成用例批量跑
3. **失败复盘**：看到卡在验证码、弹窗、权限、网络等原因
4. **对比复跑**：同一用例换设备/换版本复跑验证

---

## 5. 信息架构与页面

### 5.1 页面结构

1. **首页 / Dashboard**

* 今日任务数、通过率、Blocked 比例、Top 失败原因
* 设备在线数/占用数

2. **设备中心 / Devices**

* 设备列表（状态：在线/离线/占用/空闲）
* 设备详情（型号、系统版本、分辨率、电量、网络、最近心跳、当前任务）
* 操作：占用/释放、重连、刷新截图（仅管理员）

3. **新建任务 / New Run**

* 上传文档（拖拽）
* 选择设备（或设备池策略：自动分配）
* 运行配置：语言、max_steps、timeout、并发数（批量时）
* 安全选项：Guards 模式（严格/普通）、Take_over 策略
* 开始按钮

4. **任务详情 / Run Detail（核心）**

* 顶部：阶段条（Doc解析 → TestSpec → 编译 → 执行 → Judge → Report）
* 左侧：实时日志流 / 步骤流（steps.jsonl tail）
* 右侧：实时画面（Live View）
* 下方 Tab：

  * 用例列表（case 级）
  * 断言详情（assertion 级）
  * 证据（截图序列、final、logcat片段）
  * 运行元信息（设备/模型/版本/输入哈希/回调触发）

5. **历史任务 / Runs**

* 筛选：时间、状态、文档名、设备、标签
* 支持“复跑”（保留配置，一键创建新任务）

---

## 6. 关键交互流程

### 6.1 新建并运行（单设备）

1. QA 进入 New Run
2. 上传 PRD（或 release note）
3. 选择设备（显示是否空闲/电量/系统版本）
4. 点击开始
5. 页面跳转 Run Detail：实时显示阶段、日志、画面
6. 结束后显示 Verdict + 证据下载 + 复跑按钮

### 6.2 被 Take_over 阻塞

* Run Detail 顶部弹出明显提示：“需要人工接管：验证码/登录”
* 画面区域继续显示实时屏幕
* QA 完成手机上操作后点击 “已完成接管，继续”
* 后端收到信号后继续执行（或结束并标记 BLOCKED）

### 6.3 Guards 命中

* 顶部红色提示：“触发风险操作（发消息/支付/删号等），已阻止”
* 任务状态变为 BLOCKED
* 保留最后一屏与步骤日志

---

## 7. 功能需求（FR）

### FR-01 设备发现与状态

* 支持 ADB/HDC 设备列表获取：device_id、device_type、在线状态
* 心跳检测（建议 5s）：可截图/可输入/前台 app 名（可选）
* 设备锁（避免两任务抢同一台机）：

  * 状态：FREE / RESERVED / RUNNING / OFFLINE
  * 锁包含：run_id、占用人、开始时间
* 管理操作：释放锁、重连、标记维护

### FR-02 文档上传与管理

* 支持文件：md/txt/docx/pdf
* 上传后生成 `doc_id`，可预览抽取文本
* 解析失败时展示原因：编码/空文本/pdf 扫描导致无文本等
* 文档版本管理：同名多版本保留 hash（便于追溯）

### FR-03 任务创建（Run）

* 输入：doc_id + 设备选择 + 运行参数
* 输出：run_id + 初始状态 QUEUED
* 可选：批量运行（一个 doc 多个用例，单设备串行；v1 可先不并行）

### FR-04 实时进度与日志

* 阶段状态机（必须）：

  * `DOC_PARSING` → `SPEC_GENERATING` → `COMPILING` → `RUNNING` → `JUDGING` → `REPORTING` → `DONE`
* 实时输出：

  * 阶段事件流（百分比/子任务计数）
  * steps.jsonl tail（结构化步骤）
  * agent_verbose（原始 verbose log）
* 支持暂停/取消（v1 可先做取消）

### FR-05 实时画面（Live View）

v1 推荐实现两档（从易到难）：

**方案 A（默认，易落地）：截图轮询**

* Runner 按 `evidence_plan` 每步落盘 screenshot，同时额外以固定频率（如 1fps/2fps）生成 `live_latest.png`
* Web 前端每 500ms～1000ms 刷新 `live_latest.png`（带 cache bust 参数）
* 优点：实现极快，稳定；缺点：延迟 0.5～1s，非视频

**方案 B（增强）：WebSocket 推送帧**

* 后端把最新截图编码为 JPEG/PNG，经 WS 推送给订阅者
* 前端直接更新 `<img>` 或 canvas
* 优点：更实时；缺点：带宽与服务器压力更大

> v1 建议先 A，确保“可用”；v1.1 再上 WS/视频（WebRTC）视资源而定。

### FR-06 结果与证据浏览

* Run 结束后展示：

  * Case 级：PASS/FAIL/BLOCKED/ERROR
  * Assertion 级：逐条 must 的判定与证据指向（截图路径）
* 证据浏览：

  * 截图序列（分页/时间线）
  * final.png
  * logcat_tail（失败时）
* 一键下载：

  * 下载整包 zip（runs/<run_id>）

### FR-07 历史与复跑

* 按 doc_id/run_id/status/device 筛选
* 复跑：复制配置生成新 run（新 run_id）

### FR-08 权限（v1 简版）

* 登录（公司 SSO 可后置；v1 可用简单账号）
* 角色：

  * Viewer：只看
  * Runner：可创建任务、占用设备
  * Admin：可释放设备锁、重连、维护模式

---

## 8. 数据模型（建议）

### Device

* id, type(adb/hdc), name/model, os_version, resolution
* status(FREE/RESERVED/RUNNING/OFFLINE/MAINTENANCE)
* last_heartbeat_at, battery, network
* current_run_id, locked_by

### Document

* doc_id, filename, hash, uploaded_by, uploaded_at
* extracted_text_preview, parse_status, parse_error

### Run

* run_id, doc_id, created_by, created_at
* device_id, device_type
* stage, status(PENDING/RUNNING/DONE/FAILED/BLOCKED)
* config (lang/max_steps/timeout/guards mode)
* artifact_path, summary

### Case / Assertion（可选持久化）

* case_id, run_id, status, duration
* assertion_id, case_id, must, status, evidence_ref, why

---

## 9. 后端接口（建议契约）

### REST API（示例）

* `GET /api/devices`：设备列表

* `POST /api/devices/{id}/reserve`：占用设备

* `POST /api/devices/{id}/release`：释放设备（Admin）

* `POST /api/docs`：上传文档（multipart）

* `GET /api/docs/{doc_id}`：文档详情/预览

* `POST /api/runs`：创建 run（doc_id + device_id + config）

* `GET /api/runs/{run_id}`：run 状态与摘要

* `GET /api/runs/{run_id}/artifacts`：证据清单

* `GET /api/runs/{run_id}/download`：下载 zip

* `POST /api/runs/{run_id}/cancel`：取消

* `POST /api/runs/{run_id}/takeover/continue`：接管完成，继续

### 实时通道（WebSocket / SSE）

* `WS /ws/runs/{run_id}` 推送：

  * `stage_update`
  * `log_line`
  * `step_event`
  * `judge_event`
  * `blocked_event`（takeover/guard）
  * `done`

> v1 若你想省事：用 **SSE（Server-Sent Events）**也行；日志与事件都是单向流，SSE 足够稳定。

### 实时画面

* 轮询：`GET /api/runs/{run_id}/live.png`（返回最新截图）
* 或 WS：`WS /ws/runs/{run_id}/screen`（推送图像帧）

---

## 10. 系统实现建议（工程落地）

### 10.1 前端（Web）

* React + Next.js（或 Vue3 + Vite）
* UI：Ant Design / shadcn/ui（按团队习惯）
* 实时：WebSocket/SSE 客户端
* 图片流：轮询 `<img src="/live.png?t=...">` 或 WS

### 10.2 后端（服务端）

* FastAPI（天然支持 REST + WebSocket）
* 任务队列：Celery/RQ（或你已有任务系统）
* 存储：

  * runs 产物落磁盘或对象存储（OSS/S3）
  * 元数据进 DB（Postgres/SQLite v1 也可）

### 10.3 执行对接

* 复用你现有 Runner：调用 PhoneAgent（CLI 或 Python API）
* Runner 每步落 `steps.jsonl`、截图、final、verdict
* Web 服务只负责：启动任务、tail 日志、提供 artifact 访问

---

## 11. 安全与合规

* 默认启用 Guards 严格模式
* UI 上明确标识：此系统不会在网页端直接操作手机（v1）
* 日志脱敏：手机号、验证码、密码字段必须打码
* 下载证据包需要权限（Runner/Admin）

---

## 12. 验收标准（AC）

1. **设备可选**：Devices 页面能看到在线/占用状态，能锁定一台设备跑任务
2. **上传即跑**：上传文档后能创建 run，并看到阶段推进
3. **实时刷新**：Run Detail 上能实时看到日志与步骤流（至少 1s 内更新）
4. **实时画面可用**：能看到 live_latest 画面随运行变化（哪怕 1fps）
5. **结果可复盘**：Run 完成后能看到断言级结果与证据截图，能下载 zip
6. **Take_over 可处理**：遇到登录/验证码时 UI 提示并可点击“继续”
7. **Guard 拦截**：触发风险操作任务进入 BLOCKED，并保留最后证据

---

