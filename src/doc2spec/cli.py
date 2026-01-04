"""
Doc2Spec CLI 工具

使用 Typer 实现的命令行界面。
"""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from doc2spec.config import get_config
from doc2spec.utils import setup_logging
from doc2spec.modules.normalize import Normalizer
from doc2spec.modules.mine import RequirementMiner
from doc2spec.modules.synth import SpecSynthesizer
from doc2spec.modules.lint import Linter, lint_specs
from doc2spec.modules.export import Exporter
from doc2spec.adapters.dummy import DummyAdapter


app = typer.Typer(
    name="doc2spec",
    help="Doc → TestSpec 编译器：将文档自动转换为结构化测试规格",
    add_completion=False
)
console = Console()


def get_adapter(use_dummy: bool = False):
    """获取 LLM 适配器"""
    if use_dummy:
        return DummyAdapter(mode="mining")
    
    config = get_config()
    
    if config.llm.provider == "zhipu":
        from doc2spec.adapters.zhipu import ZhipuAdapter
        return ZhipuAdapter(
            api_key=config.llm.api_key,
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens
        )
    else:
        # 默认使用 Dummy
        return DummyAdapter(mode="mining")


@app.command()
def compile(
    input_path: Path = typer.Argument(..., help="输入文件或目录路径"),
    output: Path = typer.Option(Path("out"), "-o", "--output", help="输出目录"),
    dummy: bool = typer.Option(False, "--dummy", help="使用 Dummy LLM（调试用）"),
    no_llm: bool = typer.Option(False, "--no-llm", help="不使用 LLM，仅做直接映射"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="详细输出"),
):
    """
    编译文档为 TestSpec
    
    将 Markdown/TXT 文档编译为结构化的 TestSpec YAML 文件。
    """
    setup_logging("DEBUG" if verbose else "INFO")
    
    if not input_path.exists():
        console.print(f"[red]错误: 路径不存在 {input_path}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold blue]Doc2Spec 编译器[/bold blue]")
    console.print(f"输入: {input_path}")
    console.print(f"输出: {output}")
    console.print()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # 1. 标准化文档
        task = progress.add_task("正在解析文档...", total=None)
        normalizer = Normalizer()
        
        if input_path.is_file():
            docs = [normalizer.normalize_file(input_path)]
        else:
            docs = normalizer.normalize_directory(input_path)
        
        progress.update(task, description=f"已解析 {len(docs)} 个文档")
        
        # 2. 需求挖掘
        progress.update(task, description="正在挖掘需求...")
        adapter = get_adapter(use_dummy=dummy)
        miner = RequirementMiner(adapter=adapter)
        batches = miner.mine_from_docs(docs)
        
        total_reqs = sum(b.count for b in batches)
        progress.update(task, description=f"已提取 {total_reqs} 条需求")
        
        # 3. 规格合成
        progress.update(task, description="正在合成测试规格...")
        synth_adapter = None if no_llm else get_adapter(use_dummy=dummy)
        synthesizer = SpecSynthesizer(adapter=synth_adapter, use_llm=not no_llm)
        specs = synthesizer.synthesize_from_batches(batches)
        
        progress.update(task, description=f"已生成 {len(specs)} 个 TestSpec")
        
        # 4. Lint 校验
        progress.update(task, description="正在校验规格...")
        valid_specs, lint_results = lint_specs(specs, auto_fix=True)
        
        # 5. 导出
        progress.update(task, description="正在导出...")
        exporter = Exporter(output_dir=output)
        exporter.export(valid_specs, lint_results)
        
        progress.update(task, description="[green]完成[/green]")
    
    # 输出统计
    console.print()
    _print_summary(docs, batches, valid_specs, lint_results)


@app.command()
def lint(
    spec_path: Path = typer.Argument(..., help="TestSpec 文件或目录"),
    fix: bool = typer.Option(True, "--fix/--no-fix", help="是否自动修复"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="详细输出"),
):
    """
    校验 TestSpec 文件
    
    检查 TestSpec 是否符合规范，并可选择自动修复问题。
    """
    setup_logging("DEBUG" if verbose else "INFO")
    
    from doc2spec.models.testspec import TestSpec
    
    if not spec_path.exists():
        console.print(f"[red]错误: 路径不存在 {spec_path}[/red]")
        raise typer.Exit(1)
    
    # 加载 specs
    specs = []
    if spec_path.is_file():
        specs.append(TestSpec.from_yaml_file(str(spec_path)))
    else:
        for yaml_file in spec_path.glob("*.yaml"):
            try:
                specs.append(TestSpec.from_yaml_file(str(yaml_file)))
            except Exception as e:
                console.print(f"[yellow]警告: 无法加载 {yaml_file}: {e}[/yellow]")
    
    if not specs:
        console.print("[yellow]未找到任何 TestSpec 文件[/yellow]")
        raise typer.Exit(0)
    
    # Lint
    linter = Linter(auto_fix=fix)
    results = linter.lint_all(specs)
    
    # 输出结果
    _print_lint_results(results)
    
    # 如果有修复，保存文件
    if fix:
        for result in results:
            if result.fixed_count > 0:
                yaml_content = result.spec.model_dump_yaml()
                file_path = spec_path / f"{result.spec.id}.yaml" if spec_path.is_dir() else spec_path
                file_path.write_text(yaml_content, encoding="utf-8")
                console.print(f"[green]已保存修复: {file_path}[/green]")


@app.command("export-json")
def export_json(
    spec_dir: Path = typer.Argument(..., help="TestSpec YAML 目录"),
):
    """
    批量将 YAML 转换为 JSON
    """
    if not spec_dir.exists():
        console.print(f"[red]错误: 目录不存在 {spec_dir}[/red]")
        raise typer.Exit(1)
    
    exporter = Exporter()
    json_dir = exporter.export_json(spec_dir)
    console.print(f"[green]已导出到 {json_dir}[/green]")


@app.command()
def version():
    """显示版本信息"""
    from doc2spec import __version__
    console.print(f"doc2spec version {__version__}")


def _print_summary(docs, batches, specs, lint_results):
    """打印编译摘要"""
    table = Table(title="编译摘要")
    table.add_column("指标", style="cyan")
    table.add_column("数量", style="green")
    
    table.add_row("解析文档数", str(len(docs)))
    table.add_row("提取需求数", str(sum(b.count for b in batches)))
    table.add_row("生成 TestSpec 数", str(len(specs)))
    table.add_row("错误数", str(sum(r.error_count for r in lint_results)))
    table.add_row("警告数", str(sum(r.warning_count for r in lint_results)))
    table.add_row("自动修复数", str(sum(r.fixed_count for r in lint_results)))
    
    console.print(table)


def _print_lint_results(results):
    """打印 Lint 结果"""
    table = Table(title="Lint 结果")
    table.add_column("Spec ID", style="cyan")
    table.add_column("错误", style="red")
    table.add_column("警告", style="yellow")
    table.add_column("修复", style="green")
    
    for r in results:
        table.add_row(r.spec.id, str(r.error_count), str(r.warning_count), str(r.fixed_count))
    
    console.print(table)
    
    # 详细问题
    for r in results:
        if r.issues:
            console.print(f"\n[bold]{r.spec.id}[/bold]")
            for issue in r.issues:
                color = {"error": "red", "warning": "yellow", "info": "blue"}[issue.severity.value]
                fixed = " [已修复]" if issue.auto_fixed else ""
                console.print(f"  [{color}]{issue.code}[/{color}]: {issue.message}{fixed}")


if __name__ == "__main__":
    app()
