"""
智谱 API Adapter

调用智谱 GLM-4 API 进行 LLM 推理。
"""

import os
import logging
from doc2spec.adapters.base import LLMAdapter

logger = logging.getLogger(__name__)


class ZhipuAdapter(LLMAdapter):
    """智谱 API 适配器"""
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "glm-4",
        temperature: float = 0.1,
        max_tokens: int = 4096
    ):
        """
        初始化智谱适配器
        
        Args:
            api_key: API 密钥（默认从环境变量 ZHIPU_API_KEY 获取）
            model: 模型名称
            temperature: 温度参数（0-1，越低越稳定）
            max_tokens: 最大生成长度
        """
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        if not self.api_key:
            raise ValueError("需要提供 api_key 或设置 ZHIPU_API_KEY 环境变量")
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
    
    @property
    def name(self) -> str:
        return f"zhipu-{self.model}"
    
    @property
    def client(self):
        if self._client is None:
            try:
                from zhipuai import ZhipuAI
                self._client = ZhipuAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 zhipuai: pip install zhipuai")
        return self._client
    
    def complete(self, prompt: str, input_text: str) -> str:
        """调用智谱 API"""
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": input_text}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            content = response.choices[0].message.content
            logger.debug(f"智谱 API 响应: {content[:200]}...")
            return content
            
        except Exception as e:
            logger.error(f"智谱 API 调用失败: {e}")
            raise
