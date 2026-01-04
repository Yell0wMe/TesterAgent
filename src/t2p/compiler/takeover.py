"""
TakeoverPlanner - 接管点规划

识别需要人工接管的场景并生成规则。
"""

from doc2spec.models.testspec import TestSpec
from t2p.models.task_bundle import TakeoverPoint


# 接管触发规则库
TAKEOVER_TRIGGERS = {
    "captcha": {
        "cn": ["验证码", "图形验证", "滑动验证", "拼图验证"],
        "en": ["captcha", "verification code", "slide to verify"],
    },
    "login": {
        "cn": ["登录", "登入", "Sign in", "账号密码"],
        "en": ["login", "sign in", "log in"],
    },
    "sms_code": {
        "cn": ["短信验证码", "手机验证码", "输入验证码"],
        "en": ["sms code", "verification code", "enter code"],
    },
    "2fa": {
        "cn": ["二次验证", "两步验证", "双重认证", "安全验证"],
        "en": ["two-factor", "2fa", "two-step", "security verification"],
    },
    "biometric": {
        "cn": ["人脸识别", "指纹验证", "Face ID", "Touch ID"],
        "en": ["face recognition", "fingerprint", "face id", "touch id"],
    },
    "payment_confirm": {
        "cn": ["支付密码", "输入密码", "确认支付"],
        "en": ["payment password", "enter password", "confirm payment"],
    },
}

# 接管原因描述
TAKEOVER_REASONS = {
    "captcha": "需要人工完成验证码验证",
    "login": "需要人工完成登录认证",
    "sms_code": "需要人工输入短信验证码",
    "2fa": "需要人工完成二次验证",
    "biometric": "需要人工完成生物识别验证",
    "payment_confirm": "需要人工确认支付操作",
}


class TakeoverPlanner:
    """接管点规划器"""
    
    def __init__(self, lang: str = "cn"):
        self.lang = lang
    
    def plan(self, spec: TestSpec) -> tuple[list[TakeoverPoint], str, list[str]]:
        """
        规划接管点
        
        Args:
            spec: TestSpec
            
        Returns:
            tuple: (TakeoverPoint 列表, prompt 规则说明, 检测到的接管点名称)
        """
        points = []
        detected = []
        
        # 分析 TestSpec 内容，推断可能的接管点
        text_to_check = self._extract_text(spec)
        
        for trigger_id, keywords in TAKEOVER_TRIGGERS.items():
            trigger_keywords = keywords.get(self.lang, keywords.get("en", []))
            
            for keyword in trigger_keywords:
                if keyword.lower() in text_to_check.lower():
                    point = TakeoverPoint(
                        id=f"TO_{trigger_id}",
                        trigger=keyword,
                        reason=TAKEOVER_REASONS.get(trigger_id, f"需要人工处理: {trigger_id}")
                    )
                    points.append(point)
                    detected.append(trigger_id)
                    break  # 每种类型只检测一次
        
        # 生成 prompt 规则说明
        prompt_rules = self._create_prompt_rules(points)
        
        return points, prompt_rules, detected
    
    def _extract_text(self, spec: TestSpec) -> str:
        """提取 TestSpec 中需要检查的文本"""
        parts = [
            spec.goal.user_intent,
            spec.goal.success_state,
        ]
        
        # 添加断言目标
        for assertion in spec.assertions.ui:
            parts.append(assertion.target)
        
        # 添加步骤
        for step in spec.steps:
            parts.append(step.action)
            if step.expected:
                parts.append(step.expected)
        
        # 添加自定义前置条件
        for value in spec.preconditions.custom.values():
            if isinstance(value, str):
                parts.append(value)
        
        return " ".join(parts)
    
    def _create_prompt_rules(self, points: list[TakeoverPoint]) -> str:
        """创建接管规则的 prompt 说明"""
        if not points:
            return ""
        
        if self.lang == "cn":
            lines = [
                "以下场景必须触发 Take_over，请求人工接管：",
                ""
            ]
            
            for point in points:
                lines.append(f"🔸 {point.trigger}")
                lines.append(f"   原因：{point.reason}")
                lines.append("")
            
            lines.extend([
                "遇到上述场景时：",
                "1. 立即输出动作：Take_over",
                "2. 说明原因：\"需要人工接管: {场景}\"",
                "3. 等待人工完成操作后继续",
            ])
        else:
            lines = [
                "The following scenarios MUST trigger Take_over for manual handling:",
                ""
            ]
            
            for point in points:
                lines.append(f"🔸 {point.trigger}")
                lines.append(f"   Reason: {point.reason}")
                lines.append("")
            
            lines.extend([
                "When encountering above scenarios:",
                "1. Output action: Take_over",
                "2. Explain: \"Manual takeover needed: {scenario}\"",
                "3. Wait for human to complete and continue",
            ])
        
        return "\n".join(lines)
