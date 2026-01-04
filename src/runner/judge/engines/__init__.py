"""断言引擎"""

from runner.judge.engines.base import AssertionEngine
from runner.judge.engines.text import TextEngine

__all__ = [
    "AssertionEngine",
    "TextEngine",
]
