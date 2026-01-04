"""
RequirementItem 中间结构

用于两段式编译的中间表示，从文档中提取的可测试需求条目。
"""

from pydantic import BaseModel, Field


class SourceLoc(BaseModel):
    """源位置引用"""
    doc_id: str = Field(..., description="文档标识符")
    section: str = Field(..., description="章节路径（如 'H2: 登录 > 成功标准'）")
    paragraph: int = Field(..., ge=1, description="段落编号")
    quote: str | None = Field(default=None, description="原文引用")


class RequirementItem(BaseModel):
    """
    需求条目 - 两段式编译的中间结构
    
    A阶段（需求挖掘）的输出，B阶段（规格合成）的输入。
    """
    
    # 基本信息
    req_id: str | None = Field(
        default=None, 
        description="需求编号（若文档中已有，如 PRD-LOGIN-001）"
    )
    req_title: str = Field(..., description="需求标题")
    
    # 核心内容
    user_goal: str = Field(..., description="用户目标描述")
    success_ui: list[str] = Field(
        ..., 
        min_length=1,
        description="成功态 UI 表现（尽量具体可见）"
    )
    
    # 详细信息
    explicit_steps: list[str] = Field(
        default_factory=list, 
        description="明确步骤（若文档中有）"
    )
    preconditions: list[str] = Field(
        default_factory=list, 
        description="前置条件"
    )
    
    # 额外信号
    verifiable_signals: list[str] = Field(
        default_factory=list, 
        description="可验证信号（日志/接口/埋点）"
    )
    exceptions: list[str] = Field(
        default_factory=list, 
        description="异常情况"
    )
    danger_ops: list[str] = Field(
        default_factory=list, 
        description="危险操作"
    )
    
    # 追溯
    source_loc: SourceLoc = Field(..., description="源位置引用（必须）")
    
    # 优先级与分类
    priority: str | None = Field(
        default=None, 
        description="优先级（如 P0/P1/P2）"
    )
    category: str | None = Field(
        default=None, 
        description="分类标签"
    )

    def to_spec_id_base(self) -> str:
        """生成 Spec ID 基础部分"""
        if self.req_id:
            return self.req_id
        # 使用文档 ID 作为基础
        return f"{self.source_loc.doc_id}-TS"


class RequirementBatch(BaseModel):
    """需求批次 - A阶段输出的完整结构"""
    doc_id: str = Field(..., description="文档标识符")
    items: list[RequirementItem] = Field(default_factory=list, description="需求条目列表")
    
    @property
    def count(self) -> int:
        """需求条目数量"""
        return len(self.items)
