"""LLM 适配器模块"""

from doc2spec.adapters.base import LLMAdapter
from doc2spec.adapters.dummy import DummyAdapter

__all__ = ["LLMAdapter", "DummyAdapter"]

# 延迟导入智谱适配器，避免强制依赖
def get_zhipu_adapter():
    """获取智谱 API 适配器（需安装 zhipuai 包）"""
    from doc2spec.adapters.zhipu import ZhipuAdapter
    return ZhipuAdapter
