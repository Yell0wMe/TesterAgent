"""
Packager - 打包器

将编译结果打包为 Task Bundle。
"""

import json
from pathlib import Path
from datetime import datetime

from doc2spec.models.testspec import TestSpec
from t2p import __version__
from t2p.models.task_bundle import (
    TaskBundle, TaskConfig, PolicyConfig, CompileReport, AgentConfig,
    DiagnosticItem, GuardLevel
)
from t2p.models.observation import ObservationSpec
from t2p.compiler.parser import SpecParser
from t2p.compiler.prompt_factory import PromptFactory
from t2p.compiler.guard_weaver import GuardWeaver
from t2p.compiler.takeover import TakeoverPlanner
from t2p.compiler.budget import BudgetMapper
from t2p.compiler.observation import ObservationCompiler


class T2PCompiler:
    """T2P 编译器 - 主入口"""
    
    def __init__(self, lang: str = "cn", strict: bool = False):
        """
        初始化编译器
        
        Args:
            lang: 语言 cn/en
            strict: 严格模式
        """
        self.lang = lang
        self.strict = strict
        
        # 初始化各模块
        self.parser = SpecParser(strict=strict)
        self.prompt_factory = PromptFactory(lang=lang)
        self.guard_weaver = GuardWeaver(lang=lang)
        self.takeover_planner = TakeoverPlanner(lang=lang)
        self.budget_mapper = BudgetMapper(lang=lang)
        self.observation_compiler = ObservationCompiler()
    
    def compile(self, spec: TestSpec) -> tuple[TaskBundle, ObservationSpec]:
        """
        编译 TestSpec 为 Task Bundle
        
        Args:
            spec: 输入的 TestSpec
            
        Returns:
            tuple: (TaskBundle, ObservationSpec)
        """
        # 1. 解析和规范化
        normalized_spec, diagnostics, input_hash = self.parser.parse(spec)
        
        # 2. Guards 编译
        guard_rules, guards_desc, guard_triggers = self.guard_weaver.compile(spec.guards)
        
        # 3. Takeover 规划
        takeover_points, takeover_rules, takeover_detected = self.takeover_planner.plan(spec)
        
        # 4. Budget 映射
        agent_config, retry_config, timeout_sec = self.budget_mapper.map_from_spec(spec)
        
        # 5. Prompt 编译
        system_prompt = self.prompt_factory.create_system_prompt(guards_desc, takeover_rules)
        user_prompt = self.prompt_factory.create_user_prompt(spec)
        
        # 6. 断言编译
        observation_spec = self.observation_compiler.compile(spec)
        
        # 7. 构建 Policy
        policy = PolicyConfig(
            guards=guard_rules,
            guard_level=GuardLevel.STRICT,
            takeover_points=takeover_points,
            timeout_sec=timeout_sec,
            retry=retry_config,
            evidence_capture=[e.type.value for e in spec.evidence.required]
        )
        
        # 8. 构建 TaskConfig
        task_config = TaskConfig(
            spec_id=spec.id,
            goal=spec.goal.user_intent,
            agent_config=agent_config,
            preconditions=list(spec.preconditions.custom.values()),
            steps=[s.action for s in spec.steps],
            allow_self_planning=len(spec.steps) == 0
        )
        
        # 9. 构建 CompileReport
        compile_report = CompileReport(
            compiler_version=__version__,
            spec_id=spec.id,
            input_hash=input_hash,
            compiled_at=datetime.now(),
            diagnostics=diagnostics,
            takeover_points_detected=takeover_detected,
            guard_triggers_detected=guard_triggers
        )
        
        # 10. 构建 TaskBundle
        bundle = TaskBundle(
            spec_id=spec.id,
            bundle_id=f"{spec.id}_bundle",
            task=task_config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            policy=policy,
            compile_report=compile_report
        )
        
        return bundle, observation_spec
    
    def compile_file(self, path: str | Path) -> tuple[TaskBundle, ObservationSpec]:
        """从文件编译"""
        spec = TestSpec.from_yaml_file(str(path))
        return self.compile(spec)


class Packager:
    """打包器 - 输出 Task Bundle 目录"""
    
    def __init__(self, output_dir: str | Path = "bundles"):
        self.output_dir = Path(output_dir)
    
    def package(
        self, 
        bundle: TaskBundle, 
        observation_spec: ObservationSpec
    ) -> Path:
        """
        打包输出到目录
        
        Args:
            bundle: TaskBundle
            observation_spec: ObservationSpec
            
        Returns:
            输出目录路径
        """
        # 创建 bundle 目录
        bundle_dir = self.output_dir / bundle.bundle_id
        bundle_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        files = bundle.to_bundle_dir(str(bundle_dir))
        for filename, content in files.items():
            filepath = bundle_dir / filename
            filepath.write_text(content, encoding="utf-8")
        
        # 写入 observation_spec.json
        obs_path = bundle_dir / "observation_spec.json"
        obs_path.write_text(
            observation_spec.model_dump_json(indent=2),
            encoding="utf-8"
        )
        
        # 写入 evidence_plan.json（供 Runner 使用）
        evidence_plan = {
            "screenshot_each_step": observation_spec.capture_each_step,
            "screenshot_final": True,
            "screenshot_on_assertions": True,
            "logcat_on_error": observation_spec.capture_on_error,
            "checkpoints": [
                {
                    "id": cp.id,
                    "when": cp.when.value,
                    "capture": [c.value for c in cp.capture]
                }
                for cp in observation_spec.checkpoints
            ]
        }
        evidence_plan_path = bundle_dir / "evidence_plan.json"
        import json
        evidence_plan_path.write_text(
            json.dumps(evidence_plan, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        return bundle_dir
    
    def package_batch(
        self, 
        bundles: list[tuple[TaskBundle, ObservationSpec]]
    ) -> list[Path]:
        """批量打包"""
        paths = []
        for bundle, obs_spec in bundles:
            path = self.package(bundle, obs_spec)
            paths.append(path)
        return paths
