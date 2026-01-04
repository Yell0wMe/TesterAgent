"""
配置管理模块
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "zhipu"  # zhipu, openai, local
    model: str = "glm-4"
    api_key: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    base_url: str | None = None


@dataclass
class CompileConfig:
    """编译配置"""
    chunk_size: int = 5000  # 文本分块大小
    max_retries: int = 2    # 最大重试次数
    use_llm: bool = True    # 是否使用 LLM
    auto_fix: bool = True   # 是否自动修复


@dataclass
class Config:
    """全局配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    compile: CompileConfig = field(default_factory=CompileConfig)
    output_dir: str = "out"
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        llm_config = LLMConfig(
            provider=os.getenv("DOC2SPEC_LLM_PROVIDER", "zhipu"),
            model=os.getenv("DOC2SPEC_LLM_MODEL", "glm-4"),
            api_key=os.getenv("ZHIPU_API_KEY", ""),
            temperature=float(os.getenv("DOC2SPEC_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("DOC2SPEC_MAX_TOKENS", "4096")),
            base_url=os.getenv("DOC2SPEC_LLM_BASE_URL"),
        )
        
        compile_config = CompileConfig(
            chunk_size=int(os.getenv("DOC2SPEC_CHUNK_SIZE", "5000")),
            max_retries=int(os.getenv("DOC2SPEC_MAX_RETRIES", "2")),
            use_llm=os.getenv("DOC2SPEC_USE_LLM", "true").lower() == "true",
            auto_fix=os.getenv("DOC2SPEC_AUTO_FIX", "true").lower() == "true",
        )
        
        return cls(
            llm=llm_config,
            compile=compile_config,
            output_dir=os.getenv("DOC2SPEC_OUTPUT_DIR", "out"),
            log_level=os.getenv("DOC2SPEC_LOG_LEVEL", "INFO"),
        )


def get_config() -> Config:
    """获取配置实例"""
    return Config.from_env()
