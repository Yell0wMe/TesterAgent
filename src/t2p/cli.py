"""
T2P CLI 工具

编译 TestSpec 为 PhoneAgent 可执行的 Task Bundle。
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from doc2spec.models.testspec import TestSpec
from t2p.compiler.packager import T2PCompiler, Packager


app = typer.Typer(
    name="t2p",
    help="TestSpec → PhoneAgent 指令编译器",
    add_completion=False
)
console = Console()


@app.command()
def compile(
    input_path: Path = typer.Argument(..., help="TestSpec YAML 文件或目录"),
    output: Path = typer.Option(Path("bundles"), "-o", "--output", help="输出目录"),
    lang: str = typer.Option("cn", "--lang", help="语言 cn/en"),
    strict: bool = typer.Option(False, "--strict", help="严格模式"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="详细输出"),
):
    """
    编译 TestSpec 为 Task Bundle
    """
    if not input_path.exists():
        console.print(f"[red]错误: 路径不存在 {input_path}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold blue]T2P Compiler[/bold blue]")
    console.print(f"输入: {input_path}")
    console.print(f"输出: {output}")
    console.print()
    
    # 收集 TestSpec 文件
    spec_files = []
    if input_path.is_file():
        spec_files = [input_path]
    else:
        spec_files = list(input_path.glob("*.yaml"))
    
    if not spec_files:
        console.print("[yellow]未找到 TestSpec 文件[/yellow]")
        raise typer.Exit(0)
    
    # 编译
    compiler = T2PCompiler(lang=lang, strict=strict)
    packager = Packager(output_dir=output)
    
    results = []
    errors = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"正在编译 {len(spec_files)} 个 TestSpec...", total=None)
        
        for spec_file in spec_files:
            try:
                progress.update(task, description=f"编译 {spec_file.name}...")
                
                spec = TestSpec.from_yaml_file(str(spec_file))
                bundle, obs_spec = compiler.compile(spec)
                bundle_dir = packager.package(bundle, obs_spec)
                
                results.append({
                    "spec_id": spec.id,
                    "bundle_dir": bundle_dir,
                    "errors": bundle.compile_report.error_count,
                    "warnings": bundle.compile_report.warning_count,
                    "takeovers": len(bundle.policy.takeover_points),
                    "guards": len(bundle.policy.guards),
                })
                
            except Exception as e:
                errors.append({"file": spec_file.name, "error": str(e)})
                if verbose:
                    console.print(f"[red]错误 {spec_file.name}: {e}[/red]")
        
        progress.update(task, description="[green]完成[/green]")
    
    # 输出统计
    console.print()
    _print_summary(results, errors)


@app.command()
def version():
    """显示版本信息"""
    from t2p import __version__
    console.print(f"t2p version {__version__}")


def _print_summary(results: list, errors: list):
    """打印编译摘要"""
    table = Table(title="编译摘要")
    table.add_column("Spec ID", style="cyan")
    table.add_column("Guards", style="yellow")
    table.add_column("Takeovers", style="magenta")
    table.add_column("Warnings", style="yellow")
    table.add_column("状态", style="green")
    
    for r in results:
        table.add_row(
            r["spec_id"],
            str(r["guards"]),
            str(r["takeovers"]),
            str(r["warnings"]),
            "✓ 成功"
        )
    
    for e in errors:
        table.add_row(e["file"], "-", "-", "-", f"[red]✗ {e['error'][:30]}[/red]")
    
    console.print(table)
    
    # 总计
    console.print()
    console.print(f"成功: {len(results)}  失败: {len(errors)}")


if __name__ == "__main__":
    app()
