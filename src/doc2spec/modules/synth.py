"""
Synth 模块 - 规格合成（LLM B阶段）

将 RequirementItem 转换为 TestSpec，这是两段式编译的第二阶段。
"""

import logging
from typing import TYPE_CHECKING

import yaml

from doc2spec.models.requirement import RequirementItem, RequirementBatch
from doc2spec.models.testspec import (
    TestSpec,
    Source,
    Goal,
    Preconditions,
    AccountState,
    DeviceState,
    AppState,
    UIAssertion,
    UIAssertionType,
    MatchMode,
    Assertions,
    Guards,
    Budget,
    RetryConfig,
    RetryCondition,
    Evidence,
    EvidenceItem,
    EvidenceType,
    SafetyMode,
    DEFAULT_FORBIDDEN_OPERATIONS,
)
from doc2spec.prompts.synthesis import get_synthesis_prompt, SYNTHESIS_SYSTEM_PROMPT

if TYPE_CHECKING:
    from doc2spec.adapters.base import LLMAdapter


logger = logging.getLogger(__name__)


class SynthesisError(Exception):
    """规格合成错误"""
    pass


class SpecSynthesizer:
    """
    规格合成器
    
    将 RequirementItem 转换为 TestSpec，支持两种模式：
    1. 直接规则映射（快速，无需 LLM）
    2. LLM 增强合成（更智能，需要 LLM）
    """
    
    def __init__(
        self,
        adapter: "LLMAdapter | None" = None,
        use_llm: bool = True,
        max_retries: int = 2
    ):
        """
        初始化合成器
        
        Args:
            adapter: LLM 适配器（如果 use_llm=True 则必需）
            use_llm: 是否使用 LLM 增强合成
            max_retries: 最大重试次数
        """
        self.adapter = adapter
        self.use_llm = use_llm and adapter is not None
        self.max_retries = max_retries
        self._spec_counter = 0
    
    def synthesize(self, batch: RequirementBatch) -> list[TestSpec]:
        """
        合成一个批次的需求为 TestSpec
        
        Args:
            batch: 需求批次
            
        Returns:
            list[TestSpec]: TestSpec 列表
        """
        self._spec_counter = 0
        specs = []
        
        for item in batch.items:
            try:
                if self.use_llm:
                    spec = self._synthesize_with_llm(item)
                else:
                    spec = self._synthesize_direct(item)
                specs.append(spec)
            except Exception as e:
                logger.error(f"合成需求 '{item.req_title}' 失败: {e}")
                # 尝试降级到直接映射
                try:
                    spec = self._synthesize_direct(item)
                    specs.append(spec)
                except Exception as e2:
                    logger.error(f"降级合成也失败: {e2}")
        
        return specs
    
    def synthesize_from_batches(self, batches: list[RequirementBatch]) -> list[TestSpec]:
        """
        从多个批次合成 TestSpec
        
        Args:
            batches: 需求批次列表
            
        Returns:
            list[TestSpec]: TestSpec 列表
        """
        all_specs = []
        for batch in batches:
            specs = self.synthesize(batch)
            all_specs.extend(specs)
        return all_specs
    
    def _synthesize_direct(self, item: RequirementItem) -> TestSpec:
        """
        直接规则映射合成（无需 LLM）
        
        按照固定规则将 RequirementItem 的字段映射到 TestSpec。
        """
        self._spec_counter += 1
        
        # 生成 ID
        spec_id = self._generate_spec_id(item)
        
        # 构建 Source
        source = Source(
            doc_id=item.source_loc.doc_id,
            loc=f"{item.source_loc.section} / P{item.source_loc.paragraph}",
            quote=item.source_loc.quote
        )
        
        # 构建 Goal
        goal = Goal(
            user_intent=item.user_goal,
            success_state=item.success_ui[0] if item.success_ui else "操作成功"
        )
        
        # 构建 Preconditions
        preconditions = self._build_preconditions(item.preconditions)
        
        # 构建 Assertions
        assertions = self._build_assertions(item)
        
        # 构建 Guards
        guards = self._build_guards(item.danger_ops)
        
        # 构建 Budget（默认值）
        budget = Budget(
            max_steps=40,
            timeout_sec=180,
            retries=RetryConfig(
                max_attempts=2,
                retry_on=[RetryCondition.TIMEOUT, RetryCondition.BLOCKED_BY_POPUP],
                backoff_sec=3
            )
        )
        
        # 构建 Evidence（默认值）
        evidence = Evidence(
            required=[
                EvidenceItem(type=EvidenceType.SCREENSHOT_FINAL),
                EvidenceItem(type=EvidenceType.SCREENSHOT_ON_ASSERTIONS),
            ],
            optional=[]
        )
        
        # 构建标签
        tags = []
        if item.priority:
            tags.append(item.priority.lower())
        if item.category:
            tags.append(item.category.lower())
        
        return TestSpec(
            version="0.1",
            id=spec_id,
            title=item.req_title,
            source=[source],
            goal=goal,
            preconditions=preconditions,
            steps=[],  # 步骤暂时留空
            assertions=assertions,
            guards=guards,
            budget=budget,
            evidence=evidence,
            tags=tags,
            notes={}
        )
    
    def _synthesize_with_llm(self, item: RequirementItem) -> TestSpec:
        """使用 LLM 增强合成"""
        if not self.adapter:
            return self._synthesize_direct(item)
        
        # 构建输入
        input_text = self._format_requirement_item(item)
        prompt = get_synthesis_prompt()
        
        # 调用 LLM
        response = self._call_llm_with_retry(prompt, input_text)
        
        # 解析 YAML 响应
        spec = self._parse_yaml_response(response, item)
        
        return spec
    
    def _call_llm_with_retry(self, prompt: str, input_text: str) -> str:
        """带重试的 LLM 调用"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                full_prompt = f"{SYNTHESIS_SYSTEM_PROMPT}\n\n{prompt}"
                response = self.adapter.complete(full_prompt, input_text)
                
                # 尝试验证返回的是有效 YAML
                self._validate_yaml_response(response)
                
                return response
                
            except yaml.YAMLError as e:
                last_error = e
                logger.warning(f"第 {attempt + 1} 次尝试: YAML 解析失败，重试...")
                
                if attempt < self.max_retries:
                    prompt = f"{prompt}\n\n【重要】你必须只输出 YAML 格式，不要包含任何其他文字。"
                    
            except Exception as e:
                last_error = e
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                
                if attempt >= self.max_retries:
                    break
        
        raise SynthesisError(f"LLM 调用失败（已重试 {self.max_retries} 次）: {last_error}")
    
    def _validate_yaml_response(self, response: str) -> None:
        """验证响应是有效的 YAML"""
        cleaned = self._extract_yaml(response)
        yaml.safe_load(cleaned)
    
    def _extract_yaml(self, response: str) -> str:
        """从响应中提取 YAML 部分"""
        response = response.strip()
        
        # 如果被代码块包裹，提取内容
        if response.startswith("```"):
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        return response
    
    def _parse_yaml_response(self, response: str, item: RequirementItem) -> TestSpec:
        """解析 YAML 响应为 TestSpec"""
        cleaned = self._extract_yaml(response)
        
        try:
            data = yaml.safe_load(cleaned)
        except yaml.YAMLError as e:
            raise SynthesisError(f"无法解析 LLM 响应为 YAML: {e}")
        
        # 确保必要字段存在
        if "id" not in data:
            data["id"] = self._generate_spec_id(item)
        
        if "source" not in data:
            data["source"] = [{
                "doc_id": item.source_loc.doc_id,
                "loc": f"{item.source_loc.section} / P{item.source_loc.paragraph}"
            }]
        
        try:
            return TestSpec.model_validate(data)
        except Exception as e:
            logger.warning(f"模型验证失败，降级到直接映射: {e}")
            return self._synthesize_direct(item)
    
    def _generate_spec_id(self, item: RequirementItem) -> str:
        """生成 Spec ID"""
        base = item.to_spec_id_base()
        return f"{base}-{self._spec_counter:03d}"
    
    def _format_requirement_item(self, item: RequirementItem) -> str:
        """格式化需求项为输入文本"""
        parts = [
            f"需求标题: {item.req_title}",
            f"用户目标: {item.user_goal}",
            f"目标应用: {item.target_app or '未指定'}",
            f"目标页面: {item.target_page or '未指定'}",
            f"环境要求: {item.env_specs or '无特殊要求'}",
            f"成功态 UI: {', '.join(item.success_ui)}",
        ]
        
        if item.explicit_steps:
            parts.append(f"明确步骤: {', '.join(item.explicit_steps)}")
        
        if item.preconditions:
            parts.append(f"前置条件: {', '.join(item.preconditions)}")
        
        if item.exceptions:
            parts.append(f"异常情况: {', '.join(item.exceptions)}")
        
        if item.danger_ops:
            parts.append(f"危险操作: {', '.join(item.danger_ops)}")
        
        parts.append(f"来源: {item.source_loc.doc_id} - {item.source_loc.section}")
        
        return "\n".join(parts)
    
    def _build_preconditions(self, conditions: list[str]) -> Preconditions:
        """构建前置条件"""
        account = AccountState()
        device = DeviceState()
        app = AppState()
        custom = {}
        
        for cond in conditions:
            cond_lower = cond.lower()
            
            # 登录状态
            if "登录" in cond_lower or "login" in cond_lower:
                if "未登录" in cond_lower or "logout" in cond_lower:
                    account.state = "logged_out"
                else:
                    account.state = "logged_in"
            
            # 网络状态
            elif "网络" in cond_lower or "network" in cond_lower:
                if "无网" in cond_lower or "offline" in cond_lower:
                    device.network = "offline"
                elif "wifi" in cond_lower:
                    device.network = "wifi"
            
            # 其他作为自定义条件
            else:
                custom[f"condition_{len(custom) + 1}"] = cond
        
        return Preconditions(
            account=account,
            device=device,
            app=app,
            custom=custom
        )
    
    def _build_assertions(self, item: RequirementItem) -> Assertions:
        """构建断言"""
        ui_assertions = []
        
        for idx, success_ui in enumerate(item.success_ui, start=1):
            assertion = UIAssertion(
                id=f"A{idx}",
                type=UIAssertionType.TEXT_PRESENT,
                target=success_ui,
                match=MatchMode.CONTAINS,
                must=True,
                description=f"验证: {success_ui}"
            )
            ui_assertions.append(assertion)
        
        return Assertions(ui=ui_assertions, verifiable=[])
    
    def _build_guards(self, danger_ops: list[str]) -> Guards:
        """构建风险禁止项"""
        forbidden = DEFAULT_FORBIDDEN_OPERATIONS.copy()
        
        # 添加文档中识别的危险操作
        for op in danger_ops:
            op_normalized = op.lower().replace(" ", "_")
            if op_normalized not in forbidden:
                forbidden.append(op_normalized)
        
        return Guards(
            forbidden=forbidden,
            safety_mode=SafetyMode.STRICT
        )
