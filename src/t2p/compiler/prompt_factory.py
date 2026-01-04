"""
PromptFactory - Prompt 编译

生成测试员模式的 system_prompt 和 user_task_prompt。
"""

from pathlib import Path
from doc2spec.models.testspec import TestSpec


# 测试员模式策略补丁（中文）
TEST_MODE_PATCH_CN = """
【测试员模式 - 必须遵守】

1. 步步自检
   - 每一步执行前：确认当前界面是否符合预期
   - 每一步执行后：检查是否更接近目标断言
   - 如果偏离目标，必须解释原因并立即修正（Back/Wait）

2. 不确定就保守
   - 界面未加载完成 → Wait 等待
   - 识别不清楚 → Wait 或请求 Take_over
   - 走错路径 → 立即 Back 回退
   - 禁止"瞎点探索"和"随机尝试"

3. 预算纪律
   - 时刻关注剩余步数，接近上限时主动收敛
   - 优先完成最核心的断言验证
   - 必要时 Fail fast，不要浪费步数

4. 证据意识
   - 每个关键操作后确认界面状态
   - 成功断言前确保界面稳定
   - 失败时保留当前界面供后续分析
"""

# 测试员模式策略补丁（英文）
TEST_MODE_PATCH_EN = """
【Test Mode - MUST FOLLOW】

1. Step-by-Step Self-Check
   - Before each step: Verify current screen matches expectation
   - After each step: Check if closer to target assertions
   - If deviated, explain and correct immediately (Back/Wait)

2. When Uncertain, Be Conservative
   - Screen not loaded → Wait
   - Cannot recognize clearly → Wait or Take_over
   - Wrong path → Back immediately
   - NO random exploration or blind tapping

3. Budget Discipline
   - Monitor remaining steps, converge when approaching limit
   - Prioritize core assertion verification
   - Fail fast if necessary, don't waste steps

4. Evidence Awareness
   - Confirm screen state after key actions
   - Ensure screen stable before success assertion
   - Preserve current screen on failure for analysis
"""

# 基础系统提示词（中文）
BASE_SYSTEM_PROMPT_CN = """你是一个专业的手机自动化测试智能体。你的任务是像一个谨慎的人工测试员一样操作手机，完成指定的测试任务。

你可以执行的动作：
- Launch(app): 启动应用
- Tap(element): 点击元素
- Type(text): 输入文本
- Swipe(direction): 滑动（up/down/left/right）
- Back: 返回上一页
- Home: 返回桌面
- Wait: 等待界面加载
- Take_over: 请求人工接管（验证码/登录等场景）

重要原则：
- 每一步都要确认操作结果
- 遇到不确定的情况，选择保守策略
- 遇到无法自动化的场景（如验证码），立即 Take_over
"""

# 基础系统提示词（英文）
BASE_SYSTEM_PROMPT_EN = """You are a professional mobile automation testing agent. Your task is to operate the phone like a careful human tester to complete the specified test task.

Available actions:
- Launch(app): Launch application
- Tap(element): Tap on element
- Type(text): Input text
- Swipe(direction): Swipe (up/down/left/right)
- Back: Go back
- Home: Go to home screen
- Wait: Wait for screen to load
- Take_over: Request manual takeover (captcha/login scenarios)

Key principles:
- Verify the result of each action
- When uncertain, choose conservative strategy
- For non-automatable scenarios (e.g., captcha), Take_over immediately
"""


class PromptFactory:
    """Prompt 工厂"""
    
    def __init__(self, lang: str = "cn"):
        """
        初始化
        
        Args:
            lang: 语言 cn/en
        """
        self.lang = lang
        self.base_prompt = BASE_SYSTEM_PROMPT_CN if lang == "cn" else BASE_SYSTEM_PROMPT_EN
        self.test_mode_patch = TEST_MODE_PATCH_CN if lang == "cn" else TEST_MODE_PATCH_EN
    
    def create_system_prompt(
        self, 
        guards_desc: str,
        takeover_rules: str
    ) -> str:
        """
        创建系统提示词
        
        Args:
            guards_desc: Guards 禁区说明
            takeover_rules: 接管规则说明
            
        Returns:
            完整的系统提示词
        """
        parts = [
            self.base_prompt.strip(),
            "",
            "---",
            self.test_mode_patch.strip(),
        ]
        
        if guards_desc:
            parts.extend([
                "",
                "---【禁止区域】---",
                guards_desc.strip(),
            ])
        
        if takeover_rules:
            parts.extend([
                "",
                "---【接管规则】---",
                takeover_rules.strip(),
            ])
        
        return "\n".join(parts)
    
    def create_user_prompt(self, spec: TestSpec) -> str:
        """
        创建用户任务提示词
        
        Args:
            spec: TestSpec
            
        Returns:
            用户任务提示词
        """
        if self.lang == "cn":
            return self._create_user_prompt_cn(spec)
        else:
            return self._create_user_prompt_en(spec)
    
    def _create_user_prompt_cn(self, spec: TestSpec) -> str:
        """创建中文用户提示词"""
        parts = [
            f"【任务 ID】{spec.id}",
            "",
            f"【任务目标】",
            f"{spec.goal.user_intent}",
            f"成功状态：{spec.goal.success_state}",
            "",
        ]
        
        # 前置条件
        parts.append("【前置条件】")
        if spec.preconditions.account.state != "any":
            parts.append(f"- 账户状态：{spec.preconditions.account.state}")
        if spec.preconditions.device.network != "any":
            parts.append(f"- 网络：{spec.preconditions.device.network}")
        if spec.preconditions.app.cold_start:
            parts.append("- 冷启动应用")
        for key, value in spec.preconditions.custom.items():
            parts.append(f"- {value}")
        parts.append("")
        
        # 执行步骤
        parts.append("【执行步骤】")
        if spec.steps:
            for step in spec.steps:
                parts.append(f"{step.order}. {step.action}")
        else:
            parts.append("自主规划执行路径，但必须对齐以下断言验证点。")
        parts.append("")
        
        # 成功断言
        parts.append("【成功断言 - 必须全部通过】")
        for assertion in spec.assertions.ui:
            must_str = "[必须]" if assertion.must else "[可选]"
            parts.append(f"- {must_str} {assertion.id}: {assertion.type.value} - \"{assertion.target}\"")
        parts.append("")
        
        # 预算限制
        parts.append("【预算限制】")
        parts.append(f"- 最大步数：{spec.budget.max_steps}")
        parts.append(f"- 超时：{spec.budget.timeout_sec} 秒")
        parts.append(f"- 可重试：{spec.budget.retries.max_attempts} 次")
        parts.append("")
        
        # Guards
        if spec.guards.forbidden:
            parts.append("【禁止操作 - 触发即失败】")
            for guard in spec.guards.forbidden:
                parts.append(f"- 禁止 {guard}")
            parts.append("")
        
        return "\n".join(parts)
    
    def _create_user_prompt_en(self, spec: TestSpec) -> str:
        """创建英文用户提示词"""
        parts = [
            f"【Task ID】{spec.id}",
            "",
            f"【Goal】",
            f"{spec.goal.user_intent}",
            f"Success state: {spec.goal.success_state}",
            "",
        ]
        
        parts.append("【Preconditions】")
        if spec.preconditions.account.state != "any":
            parts.append(f"- Account: {spec.preconditions.account.state}")
        if spec.preconditions.device.network != "any":
            parts.append(f"- Network: {spec.preconditions.device.network}")
        parts.append("")
        
        parts.append("【Steps】")
        if spec.steps:
            for step in spec.steps:
                parts.append(f"{step.order}. {step.action}")
        else:
            parts.append("Self-plan execution path, but must align with assertions below.")
        parts.append("")
        
        parts.append("【Assertions - All must pass】")
        for assertion in spec.assertions.ui:
            must_str = "[MUST]" if assertion.must else "[OPT]"
            parts.append(f"- {must_str} {assertion.id}: {assertion.type.value} - \"{assertion.target}\"")
        parts.append("")
        
        parts.append("【Budget】")
        parts.append(f"- Max steps: {spec.budget.max_steps}")
        parts.append(f"- Timeout: {spec.budget.timeout_sec}s")
        parts.append("")
        
        return "\n".join(parts)
