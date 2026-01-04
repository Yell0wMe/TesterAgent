"""
Assertion Engine 基类

定义断言引擎的统一接口。
"""

from abc import ABC, abstractmethod
from typing import Any

from runner.models.verdict import AssertionResult, VerdictStatus


class AssertionEngine(ABC):
    """断言引擎抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """引擎名称"""
        pass
    
    @abstractmethod
    def evaluate(
        self,
        assertion_type: str,
        target: str,
        evidence_path: str,
        **kwargs
    ) -> AssertionResult:
        """
        评估断言
        
        Args:
            assertion_type: 断言类型（ocr_text_contains, ui_visual_element, etc.）
            target: 断言目标
            evidence_path: 证据文件路径
            **kwargs: 其他参数
            
        Returns:
            AssertionResult
        """
        pass
    
    def supports(self, assertion_type: str) -> bool:
        """
        检查是否支持该断言类型
        
        Args:
            assertion_type: 断言类型
            
        Returns:
            是否支持
        """
        return assertion_type in self.supported_types()
    
    @abstractmethod
    def supported_types(self) -> list[str]:
        """返回支持的断言类型列表"""
        pass
