"""
Reporter - 报告生成器

生成测试报告。
"""

import json
from pathlib import Path
from datetime import datetime

from runner.models.verdict import Verdict, VerdictStatus
from runner.models.report import Report, CaseResult, ReportSummary, FailureCategory
from runner.models.run_artifact import RunMeta, RunStatus


# HTML 报告模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {report_id}</title>
    <style>
        :root {{
            --pass-color: #22c55e;
            --fail-color: #ef4444;
            --blocked-color: #f59e0b;
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #e2e8f0;
            --border-color: #334155;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ font-size: 2rem; margin-bottom: 1rem; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 0.5rem;
            border: 1px solid var(--border-color);
        }}
        .stat-card h3 {{ font-size: 0.875rem; opacity: 0.7; margin-bottom: 0.5rem; }}
        .stat-card .value {{ font-size: 2rem; font-weight: bold; }}
        .stat-card.pass .value {{ color: var(--pass-color); }}
        .stat-card.fail .value {{ color: var(--fail-color); }}
        .stat-card.blocked .value {{ color: var(--blocked-color); }}
        .cases {{ background: var(--card-bg); border-radius: 0.5rem; overflow: hidden; }}
        .case-row {{
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            align-items: center;
        }}
        .case-row:last-child {{ border-bottom: none; }}
        .case-row.header {{ background: rgba(255,255,255,0.05); font-weight: bold; }}
        .status {{ padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.75rem; font-weight: bold; }}
        .status.pass {{ background: rgba(34,197,94,0.2); color: var(--pass-color); }}
        .status.fail {{ background: rgba(239,68,68,0.2); color: var(--fail-color); }}
        .status.blocked {{ background: rgba(245,158,11,0.2); color: var(--blocked-color); }}
        .meta {{ margin-top: 2rem; font-size: 0.875rem; opacity: 0.7; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 测试报告</h1>
        <p style="margin-bottom: 2rem; opacity: 0.7;">生成时间: {generated_at}</p>
        
        <div class="summary">
            <div class="stat-card">
                <h3>总用例</h3>
                <div class="value">{total}</div>
            </div>
            <div class="stat-card pass">
                <h3>通过</h3>
                <div class="value">{passed}</div>
            </div>
            <div class="stat-card fail">
                <h3>失败</h3>
                <div class="value">{failed}</div>
            </div>
            <div class="stat-card blocked">
                <h3>阻塞</h3>
                <div class="value">{blocked}</div>
            </div>
        </div>
        
        <div class="cases">
            <div class="case-row header">
                <div>用例 ID</div>
                <div>状态</div>
                <div>耗时</div>
                <div>步数</div>
                <div>接管</div>
            </div>
            {case_rows}
        </div>
        
        <div class="meta">
            <p>Report ID: {report_id}</p>
            <p>Runner Version: {runner_version}</p>
        </div>
    </div>
</body>
</html>
"""


class Reporter:
    """报告生成器"""
    
    def __init__(self):
        pass
    
    def generate(
        self,
        runs_dir: str,
        verdicts: list[Verdict] | None = None,
        output_dir: str | None = None
    ) -> Report:
        """
        生成报告
        
        Args:
            runs_dir: 运行目录
            verdicts: Verdict 列表（可选）
            output_dir: 输出目录（可选）
            
        Returns:
            Report
        """
        runs_path = Path(runs_dir)
        
        # 收集用例结果
        cases = []
        
        for run_dir in runs_path.iterdir():
            if not run_dir.is_dir():
                continue
            
            meta_path = run_dir / "meta.json"
            verdict_path = run_dir / "judge" / "verdict.json"
            
            if not meta_path.exists():
                continue
            
            # 加载 meta
            meta = RunMeta.model_validate_json(meta_path.read_text())
            
            # 加载 verdict
            verdict = None
            if verdict_path.exists():
                verdict = Verdict.model_validate_json(verdict_path.read_text())
            
            # 创建 CaseResult
            case = CaseResult(
                case_id=meta.case_id,
                run_id=meta.run_id,
                status=verdict.status if verdict else self._convert_status(meta.status),
                duration_sec=meta.duration_sec,
                step_count=0,  # TODO: 从 steps.jsonl 统计
                takeover_used=meta.takeover_count > 0,
                failed_assertions=[
                    a.id for a in (verdict.assertions if verdict else [])
                    if a.status == VerdictStatus.FAIL
                ]
            )
            
            # 失败分类
            if case.status == VerdictStatus.FAIL:
                case.failure_category = self._categorize_failure(meta, verdict)
            
            cases.append(case)
        
        # 创建报告
        report = Report(
            report_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            cases=cases
        )
        report.compute_summary()
        
        # 保存报告
        if output_dir:
            self._save_report(report, output_dir)
        
        return report
    
    def _convert_status(self, run_status: RunStatus) -> VerdictStatus:
        """转换状态"""
        if run_status == RunStatus.PASS:
            return VerdictStatus.PASS
        elif run_status == RunStatus.BLOCKED:
            return VerdictStatus.BLOCKED
        else:
            return VerdictStatus.FAIL
    
    def _categorize_failure(self, meta: RunMeta, verdict: Verdict | None) -> FailureCategory:
        """分类失败原因"""
        if meta.status == RunStatus.TIMEOUT:
            return FailureCategory.TIMEOUT
        
        if meta.exit_reason and "disconnect" in meta.exit_reason.lower():
            return FailureCategory.DEVICE_DISCONNECT
        
        if verdict and verdict.assertions:
            return FailureCategory.ASSERTION_FAILED
        
        return FailureCategory.UNKNOWN
    
    def _save_report(self, report: Report, output_dir: str) -> None:
        """保存报告"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存 JSON
        json_path = output_path / "report.json"
        json_path.write_text(report.model_dump_json(indent=2))
        
        # 生成 HTML
        html_path = output_path / "report.html"
        html_content = self._render_html(report)
        html_path.write_text(html_content)
    
    def _render_html(self, report: Report) -> str:
        """渲染 HTML 报告"""
        case_rows = ""
        for case in report.cases:
            status_class = case.status.value.lower()
            takeover = "是" if case.takeover_used else "否"
            case_rows += f"""
            <div class="case-row">
                <div>{case.case_id}</div>
                <div><span class="status {status_class}">{case.status.value}</span></div>
                <div>{case.duration_sec:.1f}s</div>
                <div>{case.step_count}</div>
                <div>{takeover}</div>
            </div>
            """
        
        return HTML_TEMPLATE.format(
            report_id=report.report_id,
            generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            total=report.summary.total,
            passed=report.summary.passed,
            failed=report.summary.failed,
            blocked=report.summary.blocked,
            case_rows=case_rows,
            runner_version=report.runner_version
        )
