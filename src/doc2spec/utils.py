"""
工具函数
"""

import logging
from pathlib import Path


def setup_logging(level: str = "INFO") -> None:
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def count_files(path: str | Path, extensions: list[str]) -> int:
    """统计指定扩展名的文件数量"""
    path = Path(path)
    if not path.exists():
        return 0
    
    count = 0
    for ext in extensions:
        count += len(list(path.glob(f"*{ext}")))
    return count
