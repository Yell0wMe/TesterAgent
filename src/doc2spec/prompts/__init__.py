"""Prompt 模板模块"""

from doc2spec.prompts.mining import get_mining_prompt, MINING_SYSTEM_PROMPT
from doc2spec.prompts.synthesis import get_synthesis_prompt, SYNTHESIS_SYSTEM_PROMPT

__all__ = [
    "get_mining_prompt",
    "MINING_SYSTEM_PROMPT",
    "get_synthesis_prompt", 
    "SYNTHESIS_SYSTEM_PROMPT",
]
