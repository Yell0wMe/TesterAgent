"""
Judge - 断言判定器

基于 ObservationSpec 和证据进行断言判定。
"""

import json
from pathlib import Path
from datetime import datetime

from t2p.models.observation import ObservationSpec, CompiledAssertion
from runner.models.run_artifact import RunArtifact
from runner.models.verdict import Verdict, AssertionResult, VerdictStatus, VerdictMeta
from runner.judge.engines.base import AssertionEngine
from runner.judge.engines.text import TextEngine


class Judge:
    """断言判定器"""
    
    def __init__(self, mock: bool = True, api_key: str = ""):
        """
        初始化
        
        Args:
            mock: 是否使用模拟模式
            api_key: API Key
        """
        self.mock = mock
        self.api_key = api_key
        
        # 注册断言引擎
        self.engines: list[AssertionEngine] = [
            TextEngine(mock=mock, api_key=api_key),
        ]
    
    def judge(
        self,
        run_dir: str,
        observation_spec: ObservationSpec | None = None
    ) -> Verdict:
        """
        对一次运行进行判定
        
        Args:
            run_dir: 运行目录
            observation_spec: ObservationSpec（可选，不提供则从目录加载）
            
        Returns:
            Verdict
        """
        run_path = Path(run_dir)
        
        # 加载 meta
        meta_path = run_path / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"meta.json 不存在: {run_dir}")
        
        from runner.models.run_artifact import RunMeta
        meta = RunMeta.model_validate_json(meta_path.read_text())
        
        # 加载 ObservationSpec
        if observation_spec is None:
            obs_path = run_path.parent.parent / "bundles" / meta.bundle_id / "observation_spec.json"
            if not obs_path.exists():
                # 尝试从当前目录的父目录查找
                obs_path = run_path / "observation_spec.json"
            
            if obs_path.exists():
                observation_spec = ObservationSpec.model_validate_json(obs_path.read_text())
            else:
                observation_spec = ObservationSpec(spec_id=meta.case_id)
        
        # 获取证据路径
        evidence_dir = run_path / "evidence" / "screenshots"
        final_screenshot = evidence_dir / "final.png"
        
        if not final_screenshot.exists():
            # 尝试获取最后一个截图
            screenshots = sorted(evidence_dir.glob("step_*.png"))
            if screenshots:
                final_screenshot = screenshots[-1]
        
        # 执行判定
        assertion_results = []
        
        for compiled_assertion in observation_spec.assertions_compiled:
            result = self._evaluate_assertion(
                assertion=compiled_assertion,
                evidence_path=str(final_screenshot) if final_screenshot.exists() else ""
            )
            assertion_results.append(result)
        
        # 计算最终状态
        status = Verdict.compute_status(assertion_results)
        
        # 生成摘要
        pass_count = sum(1 for a in assertion_results if a.status == VerdictStatus.PASS)
        fail_count = sum(1 for a in assertion_results if a.status == VerdictStatus.FAIL)
        summary = f"{pass_count} 通过, {fail_count} 失败"
        
        # 创建 Verdict
        verdict = Verdict(
            case_id=meta.case_id,
            run_id=meta.run_id,
            status=status,
            summary=summary,
            assertions=assertion_results,
            meta=VerdictMeta(
                takeover_used=meta.takeover_count > 0,
                guards_triggered=False,  # TODO: 从 events 中读取
                duration_sec=meta.duration_sec,
                engine="text"
            )
        )
        
        # 保存 verdict.json
        judge_dir = run_path / "judge"
        judge_dir.mkdir(exist_ok=True)
        verdict_path = judge_dir / "verdict.json"
        verdict_path.write_text(verdict.model_dump_json(indent=2))
        
        return verdict
    
    def _evaluate_assertion(
        self,
        assertion: CompiledAssertion,
        evidence_path: str
    ) -> AssertionResult:
        """评估单个断言"""
        
        # 查找合适的引擎
        engine = self._get_engine(assertion.type.value)
        
        if engine is None:
            return AssertionResult(
                id=assertion.id,
                original_id=assertion.original_id,
                must=assertion.must,
                status=VerdictStatus.FAIL,
                evidence=evidence_path,
                why=f"没有支持 {assertion.type.value} 的引擎"
            )
        
        # 执行评估
        result = engine.evaluate(
            assertion_type=assertion.type.value,
            target=assertion.value or "",
            evidence_path=evidence_path,
            assertion_id=assertion.id,
            must=assertion.must
        )
        result.original_id = assertion.original_id
        
        return result
    
    def _get_engine(self, assertion_type: str) -> AssertionEngine | None:
        """获取支持该断言类型的引擎"""
        for engine in self.engines:
            if engine.supports(assertion_type):
                return engine
        return None
    
    def judge_batch(self, runs_dir: str) -> list[Verdict]:
        """批量判定"""
        verdicts = []
        runs_path = Path(runs_dir)
        
        for run_dir in runs_path.iterdir():
            if run_dir.is_dir() and (run_dir / "meta.json").exists():
                try:
                    verdict = self.judge(str(run_dir))
                    verdicts.append(verdict)
                except Exception as e:
                    print(f"判定失败 {run_dir.name}: {e}")
        
        return verdicts
