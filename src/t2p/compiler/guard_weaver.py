"""
GuardWeaver - Guards 编译

将 Guards 转换为策略配置和 prompt 禁区说明。
"""

from doc2spec.models.testspec import TestSpec, Guards
from t2p.models.task_bundle import GuardRule, GuardLevel


# 风险动作词典
RISK_KEYWORDS = {
    "real_payment": {
        "cn": ["支付", "付款", "下单", "购买", "结算", "充值"],
        "en": ["pay", "payment", "checkout", "purchase", "order", "recharge"],
    },
    "account_deletion": {
        "cn": ["删除账号", "注销账号", "注销", "删除账户"],
        "en": ["delete account", "deactivate", "close account"],
    },
    "unbind_bankcard": {
        "cn": ["解绑银行卡", "解绑卡", "删除银行卡", "移除银行卡"],
        "en": ["unbind card", "remove card", "delete card"],
    },
    "send_message": {
        "cn": ["发送", "发布", "发表", "提交评论", "发消息"],
        "en": ["send", "post", "submit", "publish"],
    },
    "submit_sensitive_form": {
        "cn": ["提交表单", "确认订单", "提交申请", "确认提交"],
        "en": ["submit form", "confirm order", "submit application"],
    },
}

# 风险动作中文描述
RISK_DESCRIPTIONS = {
    "real_payment": "真实支付/付款操作",
    "account_deletion": "账号删除/注销操作",
    "unbind_bankcard": "解绑银行卡操作",
    "send_message": "发送消息/发布内容操作",
    "submit_sensitive_form": "提交敏感表单操作",
}


class GuardWeaver:
    """Guards 编译器"""
    
    def __init__(self, lang: str = "cn", level: GuardLevel = GuardLevel.STRICT):
        """
        初始化
        
        Args:
            lang: 语言 cn/en
            level: 默认 Guard 级别
        """
        self.lang = lang
        self.default_level = level
    
    def compile(self, guards: Guards) -> tuple[list[GuardRule], str, list[str]]:
        """
        编译 Guards
        
        Args:
            guards: TestSpec 中的 Guards
            
        Returns:
            tuple: (GuardRule 列表, prompt 禁区说明, 检测到的触发词)
        """
        rules = []
        detected_triggers = []
        
        for forbidden in guards.forbidden:
            rule = self._create_rule(forbidden)
            rules.append(rule)
            detected_triggers.append(forbidden)
        
        # 生成 prompt 禁区说明
        prompt_desc = self._create_prompt_description(rules)
        
        return rules, prompt_desc, detected_triggers
    
    def _create_rule(self, forbidden: str) -> GuardRule:
        """创建单条 Guard 规则"""
        # 获取关键词
        keywords_dict = RISK_KEYWORDS.get(forbidden, {})
        keywords = keywords_dict.get(self.lang, [])
        
        # 如果没有预定义关键词，使用原始值
        if not keywords:
            keywords = [forbidden]
        
        return GuardRule(
            id=f"G_{forbidden}",
            name=RISK_DESCRIPTIONS.get(forbidden, forbidden),
            keywords=keywords,
            level=self.default_level
        )
    
    def _create_prompt_description(self, rules: list[GuardRule]) -> str:
        """创建 prompt 禁区说明"""
        if not rules:
            return ""
        
        if self.lang == "cn":
            lines = ["以下操作被禁止，一旦检测到相关界面/操作，必须立即停止并报告：", ""]
            for rule in rules:
                keywords_str = "、".join(rule.keywords[:3])
                lines.append(f"❌ {rule.name}")
                lines.append(f"   关键词：{keywords_str}")
                lines.append("")
            
            lines.extend([
                "触发禁区时的处理方式：",
                "1. 立即停止当前操作",
                "2. 输出警告：\"触发禁止操作: {操作名称}\"",
                "3. 等待确认回调或直接标记任务为 blocked",
            ])
        else:
            lines = ["The following operations are FORBIDDEN. Stop immediately if detected:", ""]
            for rule in rules:
                keywords_str = ", ".join(rule.keywords[:3])
                lines.append(f"❌ {rule.name}")
                lines.append(f"   Keywords: {keywords_str}")
                lines.append("")
            
            lines.extend([
                "When guard triggered:",
                "1. Stop current operation immediately",
                "2. Output warning: \"Guard triggered: {operation}\"",
                "3. Wait for confirmation callback or mark task as blocked",
            ])
        
        return "\n".join(lines)
    
    def check_text_for_guards(self, text: str, rules: list[GuardRule]) -> list[str]:
        """
        检查文本是否触发 Guards
        
        Args:
            text: 要检查的文本
            rules: Guard 规则列表
            
        Returns:
            触发的 Guard ID 列表
        """
        triggered = []
        text_lower = text.lower()
        
        for rule in rules:
            for keyword in rule.keywords:
                if keyword.lower() in text_lower:
                    triggered.append(rule.id)
                    break
        
        return triggered
