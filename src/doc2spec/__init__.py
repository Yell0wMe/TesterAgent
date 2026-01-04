"""
Doc2Spec - 文档到测试规格编译器

将自然语言产品/研发文档自动转换为结构化 TestSpec，
形成可执行、可判定、可追溯的验收契约。
"""

__version__ = "0.1.0"
__author__ = "TesterAgent Team"

from doc2spec.models.testspec import TestSpec
from doc2spec.models.requirement import RequirementItem

__all__ = ["TestSpec", "RequirementItem", "__version__"]
