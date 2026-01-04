"""
TestSpec DSL Pydantic 模型

定义测试规格的完整数据结构，包含：
- 目标、前置条件、断言、证据、风险禁止项、预算与重试策略
"""

from typing import Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ============== 断言类型枚举 ==============

class UIAssertionType(str, Enum):
    """UI 断言类型"""
    TEXT_PRESENT = "ui_text_present"
    TEXT_ABSENT = "ui_text_absent"
    TOAST_PRESENT = "ui_toast_present"
    SCREEN_LANDMARK = "ui_screen_landmark"
    ELEMENT_STATE = "ui_element_state"
    COUNT = "ui_count"


class MatchMode(str, Enum):
    """文本匹配模式"""
    CONTAINS = "contains"
    EQUALS = "equals"
    REGEX = "regex"


class VerifiableAssertionType(str, Enum):
    """可验证断言类型（预留接口）"""
    LOGCAT_CONTAINS = "logcat_contains"
    HTTP_API = "http_api"
    BACKEND_STATE = "backend_state"
    ANALYTICS_EVENT = "analytics_event"


class EvidenceType(str, Enum):
    """证据类型"""
    SCREENSHOT_FINAL = "screenshot_final"
    SCREENSHOT_ON_ASSERTIONS = "screenshot_on_assertions"
    SCREENSHOT_EACH_STEP = "screenshot_each_step"
    LOGCAT_TAIL = "logcat_tail"
    UI_TREE_DUMP = "ui_tree_dump"
    SCREEN_RECORDING = "screen_recording"


class RetryCondition(str, Enum):
    """重试条件"""
    TIMEOUT = "timeout"
    BLOCKED_BY_POPUP = "blocked_by_popup"
    ASSERTION_FAILED = "assertion_failed"
    NETWORK_ERROR = "network_error"


class SafetyMode(str, Enum):
    """安全模式"""
    STRICT = "strict"
    NORMAL = "normal"
    PERMISSIVE = "permissive"


# ============== 子模型定义 ==============

class Source(BaseModel):
    """文档引用"""
    doc_id: str = Field(..., description="文档标识符")
    loc: str = Field(..., description="文档位置（如 'H2: 登录 > 成功标准 / P3'）")
    quote: str | None = Field(default=None, description="原文引用（可选）")


class Goal(BaseModel):
    """用户目标与成功态"""
    user_intent: str = Field(..., description="用户意图描述")
    success_state: str = Field(..., description="成功状态描述")


class AccountState(BaseModel):
    """账户状态"""
    state: Literal["logged_in", "logged_out", "any"] = Field(
        default="any", description="登录状态"
    )
    user_type: str | None = Field(default=None, description="用户类型（如 VIP、普通用户）")


class DeviceState(BaseModel):
    """设备状态"""
    network: Literal["wifi", "4g", "5g", "offline", "any"] = Field(
        default="any", description="网络状态"
    )
    region: str = Field(default="any", description="地区")
    os_version: str | None = Field(default=None, description="系统版本")


class AppState(BaseModel):
    """应用状态"""
    install_state: Literal["installed", "not_installed", "any"] = Field(
        default="installed", description="安装状态"
    )
    cold_start: bool = Field(default=True, description="是否冷启动")
    version: str | None = Field(default=None, description="应用版本")


class Preconditions(BaseModel):
    """前置条件"""
    account: AccountState = Field(default_factory=AccountState)
    device: DeviceState = Field(default_factory=DeviceState)
    app: AppState = Field(default_factory=AppState)
    custom: dict[str, Any] = Field(default_factory=dict, description="自定义前置条件")


class UIAssertion(BaseModel):
    """UI 断言"""
    id: str = Field(..., description="断言唯一标识")
    type: UIAssertionType = Field(..., description="断言类型")
    target: str = Field(..., description="断言目标（文本/元素描述）")
    match: MatchMode = Field(default=MatchMode.CONTAINS, description="匹配模式")
    must: bool = Field(default=True, description="是否必须通过")
    description: str | None = Field(default=None, description="断言说明")


class VerifiableAssertion(BaseModel):
    """可验证断言（预留接口）"""
    id: str = Field(..., description="断言唯一标识")
    type: VerifiableAssertionType = Field(..., description="断言类型")
    target: str = Field(..., description="断言目标")
    expected: str | None = Field(default=None, description="预期值")
    must: bool = Field(default=False, description="是否必须通过")
    config: dict[str, Any] = Field(default_factory=dict, description="额外配置")


class Assertions(BaseModel):
    """断言集合"""
    ui: list[UIAssertion] = Field(default_factory=list, description="UI 断言列表")
    verifiable: list[VerifiableAssertion] = Field(
        default_factory=list, description="可验证断言列表"
    )


class Guards(BaseModel):
    """风险禁止项"""
    forbidden: list[str] = Field(
        default_factory=list,
        description="禁止操作列表"
    )
    safety_mode: SafetyMode = Field(
        default=SafetyMode.STRICT,
        description="安全模式"
    )


class RetryConfig(BaseModel):
    """重试配置"""
    max_attempts: int = Field(default=2, ge=0, le=10, description="最大重试次数")
    retry_on: list[RetryCondition] = Field(
        default_factory=lambda: [RetryCondition.TIMEOUT, RetryCondition.BLOCKED_BY_POPUP],
        description="触发重试的条件"
    )
    backoff_sec: int = Field(default=3, ge=0, description="重试间隔秒数")


class Budget(BaseModel):
    """执行预算"""
    max_steps: int = Field(default=40, gt=0, description="最大步骤数")
    timeout_sec: int = Field(default=180, gt=0, description="超时秒数")
    retries: RetryConfig = Field(default_factory=RetryConfig, description="重试配置")


class EvidenceItem(BaseModel):
    """证据项"""
    type: EvidenceType = Field(..., description="证据类型")
    config: dict[str, Any] = Field(default_factory=dict, description="额外配置")


class Evidence(BaseModel):
    """证据采集要求"""
    required: list[EvidenceItem] = Field(default_factory=list, description="必须采集的证据")
    optional: list[EvidenceItem] = Field(default_factory=list, description="可选采集的证据")


class Step(BaseModel):
    """执行步骤（可选）"""
    order: int = Field(..., description="步骤顺序")
    action: str = Field(..., description="操作描述")
    expected: str | None = Field(default=None, description="预期结果")


# ============== 主模型 ==============

class TestSpec(BaseModel):
    """TestSpec DSL 主模型 - 验收契约"""
    
    # 元数据
    version: str = Field(default="0.1", description="DSL 版本")
    id: str = Field(..., description="全局唯一标识符")
    title: str = Field(..., description="用例标题")
    
    # 追溯信息
    source: list[Source] = Field(..., min_length=1, description="文档引用")
    
    # 核心内容
    goal: Goal = Field(..., description="用户目标与成功态")
    preconditions: Preconditions = Field(
        default_factory=Preconditions, description="前置条件"
    )
    steps: list[Step] = Field(default_factory=list, description="执行步骤")
    assertions: Assertions = Field(..., description="断言集合")
    
    # 安全与执行控制
    guards: Guards = Field(default_factory=Guards, description="风险禁止项")
    budget: Budget = Field(default_factory=Budget, description="执行预算")
    evidence: Evidence = Field(default_factory=Evidence, description="证据采集要求")
    
    # 扩展
    tags: list[str] = Field(default_factory=list, description="标签")
    notes: dict[str, Any] = Field(default_factory=dict, description="备注")

    @field_validator("assertions")
    @classmethod
    def validate_ui_assertions_not_empty(cls, v: Assertions) -> Assertions:
        """校验 UI 断言不能为空"""
        if not v.ui:
            raise ValueError("assertions.ui 不能为空，至少需要 1 条 UI 断言")
        return v

    def model_dump_yaml(self) -> str:
        """导出为 YAML 格式"""
        import yaml
        data = self.model_dump(mode="json", exclude_none=True)
        return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "TestSpec":
        """从 YAML 字符串加载"""
        import yaml
        data = yaml.safe_load(yaml_str)
        return cls.model_validate(data)

    @classmethod
    def from_yaml_file(cls, path: str) -> "TestSpec":
        """从 YAML 文件加载"""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_yaml(f.read())


# ============== 默认值常量 ==============

DEFAULT_FORBIDDEN_OPERATIONS = [
    "real_payment",
    "account_deletion",
    "unbind_bankcard",
    "send_message",
    "submit_sensitive_form",
]

DEFAULT_REQUIRED_EVIDENCE = [
    EvidenceItem(type=EvidenceType.SCREENSHOT_FINAL),
    EvidenceItem(type=EvidenceType.SCREENSHOT_ON_ASSERTIONS),
]


def create_default_guards() -> Guards:
    """创建默认的风险禁止项"""
    return Guards(
        forbidden=DEFAULT_FORBIDDEN_OPERATIONS.copy(),
        safety_mode=SafetyMode.STRICT
    )


def create_default_evidence() -> Evidence:
    """创建默认的证据采集要求"""
    return Evidence(required=DEFAULT_REQUIRED_EVIDENCE.copy(), optional=[])


def create_default_budget() -> Budget:
    """创建默认的执行预算"""
    return Budget(
        max_steps=40,
        timeout_sec=180,
        retries=RetryConfig(
            max_attempts=2,
            retry_on=[RetryCondition.TIMEOUT, RetryCondition.BLOCKED_BY_POPUP],
            backoff_sec=3
        )
    )
