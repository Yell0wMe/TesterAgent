"""
Export 模块 - 导出功能

将 TestSpec 导出为 YAML 文件和 index.json 追溯映射。
"""

import json
import logging
from pathlib import Path
from datetime import datetime

import yaml

from doc2spec.models.testspec import TestSpec
from doc2spec.modules.lint import LintResult

logger = logging.getLogger(__name__)


class Exporter:
    """TestSpec 导出器"""
    
    def __init__(self, output_dir: str | Path = "out"):
        self.output_dir = Path(output_dir)
        self.specs_dir = self.output_dir / "specs"
    
    def export(self, specs: list[TestSpec], lint_results: list[LintResult] | None = None) -> Path:
        """
        导出 TestSpec 列表
        
        Args:
            specs: TestSpec 列表
            lint_results: 可选的 Lint 结果（用于统计）
            
        Returns:
            Path: 输出目录路径
        """
        # 创建目录
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        
        # 导出每个 spec
        index_entries = []
        for spec in specs:
            yaml_path = self._export_spec(spec)
            index_entries.append({
                "spec_id": spec.id,
                "title": spec.title,
                "source": [s.model_dump() for s in spec.source],
                "file": str(yaml_path.relative_to(self.output_dir)),
                "tags": spec.tags
            })
        
        # 生成 index.json
        self._export_index(index_entries, lint_results)
        
        logger.info(f"已导出 {len(specs)} 个 TestSpec 到 {self.output_dir}")
        return self.output_dir
    
    def _export_spec(self, spec: TestSpec) -> Path:
        """导出单个 spec 为 YAML"""
        filename = f"{spec.id}.yaml"
        filepath = self.specs_dir / filename
        
        yaml_content = spec.model_dump_yaml()
        filepath.write_text(yaml_content, encoding="utf-8")
        
        return filepath
    
    def _export_index(self, entries: list[dict], lint_results: list[LintResult] | None) -> Path:
        """导出 index.json"""
        index_path = self.output_dir / "index.json"
        
        # 统计信息
        stats = {
            "total_specs": len(entries),
            "generated_at": datetime.now().isoformat(),
            "version": "0.1"
        }
        
        if lint_results:
            stats["lint_summary"] = {
                "total_errors": sum(r.error_count for r in lint_results),
                "total_warnings": sum(r.warning_count for r in lint_results),
                "total_fixed": sum(r.fixed_count for r in lint_results)
            }
        
        index_data = {
            "stats": stats,
            "specs": entries
        }
        
        index_path.write_text(
            json.dumps(index_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        return index_path
    
    def export_json(self, specs_dir: str | Path) -> Path:
        """批量将 YAML 转换为 JSON"""
        specs_dir = Path(specs_dir)
        json_dir = specs_dir.parent / "specs_json"
        json_dir.mkdir(parents=True, exist_ok=True)
        
        count = 0
        for yaml_file in specs_dir.glob("*.yaml"):
            try:
                spec = TestSpec.from_yaml_file(str(yaml_file))
                json_path = json_dir / f"{yaml_file.stem}.json"
                json_path.write_text(
                    spec.model_dump_json(indent=2),
                    encoding="utf-8"
                )
                count += 1
            except Exception as e:
                logger.error(f"转换失败 {yaml_file}: {e}")
        
        logger.info(f"已转换 {count} 个文件到 {json_dir}")
        return json_dir
