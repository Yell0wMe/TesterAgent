"""
Runner CLI 工具

执行测试、判定断言、生成报告。
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

import os
from dotenv import load_dotenv

from runner.executor.runner import TaskRunner
from runner.judge.judge import Judge
from runner.reporter.reporter import Reporter


app = typer.Typer(
    name="runner",
    help="测试执行与判定框架",
    add_completion=False
)
console = Console()


@app.command()
def run(
    bundle_dir: Path = typer.Argument(..., help="Task Bundle 目录"),
    device_id: str = typer.Option("mock", "--device-id", "-d", help="设备 ID"),
    output: Path = typer.Option(Path("runs"), "-o", "--output", help="输出目录"),
    mock: bool = typer.Option(True, "--mock/--no-mock", help="使用模拟模式"),
    use_agent: bool = typer.Option(True, "--use-agent/--no-agent", help="使用 PhoneAgent 执行"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="详细输出"),
):
    """
    执行单个 Task Bundle
    
    --use-agent: 使用 PhoneAgentAdapter 执行（推荐）
    --no-agent: 使用旧版 Mock 执行
    """
    if not bundle_dir.exists():
        console.print(f"[red]错误: 目录不存在 {bundle_dir}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold blue]Runner[/bold blue]")
    console.print(f"Bundle: {bundle_dir}")
    console.print(f"设备: {device_id}")
    console.print(f"模式: {'Mock' if mock else '真实'}")
    console.print(f"执行器: {'PhoneAgent' if use_agent else '传统'}")
    console.print()
    
    # 加载环境变量
    load_dotenv()
    api_key = os.getenv("ZHIPU_API_KEY", "")
    
    # 执行
    runner = TaskRunner(runs_dir=str(output), mock=mock, verbose=verbose, api_key=api_key, use_agent=use_agent)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("执行中...", total=None)
        
        # 根据选项选择执行方式
        if use_agent:
            artifact = runner.run_with_agent(str(bundle_dir), device_id if device_id != "mock" else None)
        else:
            artifact = runner.run(str(bundle_dir), device_id)
        
        progress.update(task, description=f"[green]完成 - {artifact.meta.status.value}[/green]")
    
    # 输出结果
    console.print()
    _print_run_result(artifact)
    
    # 自动判定
    if artifact.meta.status.value in ["pass", "fail", "finished"]:
        console.print("\n[bold]执行判定...[/bold]")
        judge = Judge(mock=mock, api_key=api_key)
        verdict = judge.judge(artifact.artifact_dir)
        _print_verdict(verdict)


@app.command()
def batch(
    bundles_dir: Path = typer.Argument(..., help="Task Bundle 根目录"),
    output: Path = typer.Option(Path("runs"), "-o", "--output", help="输出目录"),
    parallel: int = typer.Option(1, "--parallel", "-p", help="并行数"),
    mock: bool = typer.Option(True, "--mock/--no-mock", help="使用模拟模式"),
    use_agent: bool = typer.Option(True, "--use-agent/--no-agent", help="使用 PhoneAgent 执行"),
):
    """
    批量执行 Task Bundle
    """
    if not bundles_dir.exists():
        console.print(f"[red]错误: 目录不存在 {bundles_dir}[/red]")
        raise typer.Exit(1)
    
    # 收集 bundles
    bundle_dirs = [d for d in bundles_dir.iterdir() if d.is_dir() and (d / "task.json").exists()]
    
    if not bundle_dirs:
        console.print("[yellow]未找到 Task Bundle[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"[bold blue]Batch Runner[/bold blue]")
    console.print(f"找到 {len(bundle_dirs)} 个 Bundle")
    console.print(f"执行器: {'PhoneAgent' if use_agent else '传统'}")
    console.print()
    
    # 执行
    # 加载环境变量
    load_dotenv()
    api_key = os.getenv("ZHIPU_API_KEY", "")
    
    runner = TaskRunner(runs_dir=str(output), mock=mock, api_key=api_key, use_agent=use_agent)
    judge = Judge(mock=mock, api_key=api_key)
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("执行中...", total=len(bundle_dirs))
        
        for bundle_dir in bundle_dirs:
            progress.update(task, description=f"执行 {bundle_dir.name}...")
            
            try:
                # 根据选项选择执行方式
                if use_agent:
                    artifact = runner.run_with_agent(str(bundle_dir))
                else:
                    artifact = runner.run(str(bundle_dir))
                    
                verdict = judge.judge(artifact.artifact_dir)
                results.append({
                    "case_id": artifact.meta.case_id,
                    "status": verdict.status.value,
                    "duration": artifact.meta.duration_sec
                })
            except Exception as e:
                results.append({
                    "case_id": bundle_dir.name,
                    "status": "ERROR",
                    "duration": 0,
                    "error": str(e)
                })
            
            progress.advance(task)
    
    # 生成报告
    reporter = Reporter()
    report = reporter.generate(str(output), output_dir=str(output / "report"))
    
    # 输出摘要
    console.print()
    _print_batch_summary(results, report)


@app.command()
def judge(
    run_dir: Path = typer.Argument(..., help="运行目录"),
    mock: bool = typer.Option(True, "--mock/--no-mock", help="使用模拟模式"),
):
    """
    对运行结果进行判定
    """
    if not run_dir.exists():
        console.print(f"[red]错误: 目录不存在 {run_dir}[/red]")
        raise typer.Exit(1)
    
    # 加载环境变量
    load_dotenv()
    api_key = os.getenv("ZHIPU_API_KEY", "")
    
    judge_instance = Judge(mock=mock, api_key=api_key)
    verdict = judge_instance.judge(str(run_dir))
    
    _print_verdict(verdict)


@app.command()
def report(
    runs_dir: Path = typer.Argument(..., help="运行目录"),
    output: Path = typer.Option(None, "-o", "--output", help="输出目录"),
):
    """
    生成测试报告
    """
    if not runs_dir.exists():
        console.print(f"[red]错误: 目录不存在 {runs_dir}[/red]")
        raise typer.Exit(1)
    
    reporter = Reporter()
    output_dir = str(output) if output else str(runs_dir / "report")
    report_obj = reporter.generate(str(runs_dir), output_dir=output_dir)
    
    console.print(f"[green]报告已生成: {output_dir}[/green]")
    console.print(f"  - report.json")
    console.print(f"  - report.html")


@app.command()
def version():
    """显示版本信息"""
    from runner import __version__
    console.print(f"runner version {__version__}")


def _print_run_result(artifact):
    """打印运行结果"""
    table = Table(title="运行结果")
    table.add_column("项目", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("Run ID", artifact.meta.run_id)
    table.add_row("Case ID", artifact.meta.case_id)
    table.add_row("状态", artifact.meta.status.value)
    table.add_row("步数", str(artifact.step_count))
    table.add_row("耗时", f"{artifact.meta.duration_sec:.2f}s")
    table.add_row("接管次数", str(artifact.meta.takeover_count))
    
    console.print(table)


def _print_verdict(verdict):
    """打印判定结果"""
    status_color = {"PASS": "green", "FAIL": "red", "BLOCKED": "yellow"}.get(verdict.status.value, "white")
    
    console.print(f"\n[bold]判定结果: [{status_color}]{verdict.status.value}[/{status_color}][/bold]")
    console.print(f"摘要: {verdict.summary}")
    
    if verdict.assertions:
        console.print("\n断言详情:")
        for a in verdict.assertions:
            status_icon = "✓" if a.status.value == "PASS" else "✗"
            color = "green" if a.status.value == "PASS" else "red"
            console.print(f"  [{color}]{status_icon}[/{color}] {a.id}: {a.why}")


def _print_batch_summary(results, report):
    """打印批量执行摘要"""
    table = Table(title="执行摘要")
    table.add_column("用例", style="cyan")
    table.add_column("状态")
    table.add_column("耗时")
    
    for r in results:
        status = r["status"]
        color = {"PASS": "green", "FAIL": "red", "BLOCKED": "yellow"}.get(status, "white")
        table.add_row(
            r["case_id"],
            f"[{color}]{status}[/{color}]",
            f"{r['duration']:.2f}s"
        )
    
    console.print(table)
    
    console.print(f"\n总计: {report.summary.total} | "
                  f"[green]通过: {report.summary.passed}[/green] | "
                  f"[red]失败: {report.summary.failed}[/red] | "
                  f"[yellow]阻塞: {report.summary.blocked}[/yellow]")


if __name__ == "__main__":
    app()
