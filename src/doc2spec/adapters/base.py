"""
LLM Adapter 基类

定义统一的 LLM 调用接口。
"""

from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """LLM 适配器基类"""
    
    @abstractmethod
    def complete(self, prompt: str, input_text: str) -> str:
        """
        调用 LLM 生成响应
        
        Args:
            prompt: 系统提示词
            input_text: 用户输入文本
            
        Returns:
            str: LLM 生成的响应
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称"""
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
