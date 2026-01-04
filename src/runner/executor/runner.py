"""
Task Runner - 任务执行器

执行 Task Bundle，采集证据，生成 Run Artifact。
"""

import os
import json
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any

from t2p.models.task_bundle import TaskBundle, PolicyConfig
from t2p.models.observation import ObservationSpec
from runner.models.run_artifact import RunArtifact, RunMeta, RunStatus, StepRecord
from runner.executor.device import Device, MockDevice, DeviceManager
from runner.executor.evidence import EvidenceCollector
from runner.executor.callbacks import CallbackHandler


# 模拟动作序列（Mock 模式）
MOCK_ACTIONS = [
    {"name": "Launch", "args": {"package": "com.example.app"}},
    {"name": "Wait", "args": {"seconds": 1}},
    {"name": "Tap", "args": {"x": 540, "y": 960}},
    {"name": "Type", "args": {"text": "test_input"}},
    {"name": "Tap", "args": {"x": 540, "y": 1200}},
    {"name": "Wait", "args": {"seconds": 1}},
]


class TaskRunner:
    """任务执行器"""
    
    def __init__(
        self,
        runs_dir: str = "runs",
        mock: bool = True,
        verbose: bool = False,
        api_key: str = "",
        use_agent: bool = False
    ):
        """
        初始化
        
        Args:
            runs_dir: 运行输出目录
            mock: 是否使用 Mock 模式
            verbose: 详细输出
            api_key: PhoneAgent API Key
            use_agent: 是否使用 PhoneAgentAdapter
        """
        self.runs_dir = Path(runs_dir)
        self.mock = mock
        self.verbose = verbose
        self.api_key = api_key
        self.use_agent = use_agent
        self.adapter = None
        
    def stop(self):
        """停止任务"""
        if self.adapter:
            self.adapter.stop()
        
        self.device_manager = DeviceManager()
        
        # PhoneAgent Adapter
        if use_agent:
            from runner.executor.phoneagent_adapter import PhoneAgentAdapter
            self.agent_adapter = PhoneAgentAdapter(mock=mock)
        else:
            self.agent_adapter = None
    
    def run(
        self,
        bundle_dir: str,
        device_id: str = "mock"
    ) -> RunArtifact:
        """
        执行 Task Bundle
        
        Args:
            bundle_dir: Task Bundle 目录
            device_id: 设备 ID
            
        Returns:
            RunArtifact
        """
        bundle_path = Path(bundle_dir)
        
        # 加载 Bundle
        bundle = self._load_bundle(bundle_path)
        observation_spec = self._load_observation_spec(bundle_path)
        
        # 生成 run_id
        run_id = self._generate_run_id(bundle.spec_id)
        
        # 创建运行目录
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        device = self._get_device(device_id)
        evidence = EvidenceCollector(str(run_dir / "evidence"))
        callbacks = CallbackHandler(
            auto_confirm=self.mock,
            auto_takeover=self.mock
        )
        
        # 创建 RunArtifact
        artifact = RunArtifact(
            meta=RunMeta(
                run_id=run_id,
                case_id=bundle.spec_id,
                bundle_id=bundle.bundle_id,
                device_id=device.device_id,
                device_type=device.device_type,
                max_steps=bundle.task.agent_config.max_steps,
                timeout_sec=bundle.policy.timeout_sec,
                started_at=datetime.now(),
                status=RunStatus.RUNNING
            ),
            artifact_dir=str(run_dir),
            evidence_dir=str(run_dir / "evidence")
        )
        
        # 执行任务
        try:
            self._execute(
                artifact=artifact,
                bundle=bundle,
                observation_spec=observation_spec,
                device=device,
                evidence=evidence,
                callbacks=callbacks
            )
        except Exception as e:
            artifact.finish(RunStatus.ERROR, str(e))
            if self.verbose:
                print(f"执行错误: {e}")
        
        # 更新回调统计
        artifact.meta.takeover_count = callbacks.takeover_count
        artifact.meta.takeover_duration_sec = callbacks.takeover_duration_sec
        artifact.events.extend(callbacks.events)
        
        # 保存产物
        self._save_artifact(artifact, run_dir)
        
        return artifact
    
    def _execute(
        self,
        artifact: RunArtifact,
        bundle: TaskBundle,
        observation_spec: ObservationSpec,
        device: Device,
        evidence: EvidenceCollector,
        callbacks: CallbackHandler
    ) -> None:
        """执行任务核心逻辑"""
        max_steps = bundle.task.agent_config.max_steps
        timeout_sec = bundle.policy.timeout_sec
        start_time = time.time()
        
        # Mock 模式：使用模拟动作
        if self.mock:
            actions = self._generate_mock_actions(max_steps)
        else:
            # 真实模式：调用 PhoneAgent（暂未实现）
            actions = MOCK_ACTIONS
        
        # 执行每个动作
        for i, action in enumerate(actions):
            # 检查步数限制
            if i >= max_steps:
                artifact.finish(RunStatus.PASS, f"达到最大步数 {max_steps}")
                break
            
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > timeout_sec:
                evidence.capture_final_screenshot(device)
                artifact.finish(RunStatus.TIMEOUT, f"超时 {timeout_sec}s")
                return
            
            # 检查 Take_over
            if action.get("name") == "Take_over":
                callbacks.takeover_callback(action.get("reason", "需要人工接管"))
                continue
            
            # 执行动作
            step_start = time.time()
            success = self._execute_action(device, action)
            latency = int((time.time() - step_start) * 1000)
            
            # 采集截图
            screen_path = evidence.capture_step_screenshot(device, i)
            
            # 记录步骤
            step = artifact.add_step(
                action=action,
                screen=screen_path,
                latency_ms=latency
            )
            step.status = "ok" if success else "error"
            
            if self.verbose:
                print(f"  Step {i}: {action.get('name')} -> {step.status}")
        
        # 采集最终截图
        evidence.capture_final_screenshot(device)
        
        # 完成
        if not artifact.is_finished:
            artifact.finish(RunStatus.PASS, "执行完成")
    
    def _execute_action(self, device: Device, action: dict) -> bool:
        """执行单个动作"""
        name = action.get("name", "")
        args = action.get("args", {})
        
        if name == "Launch":
            return device.launch_app(args.get("package", ""))
        elif name == "Tap":
            return device.tap(args.get("x", 0), args.get("y", 0))
        elif name == "Type":
            return device.input_text(args.get("text", ""))
        elif name == "Swipe":
            return device.swipe(
                args.get("x1", 0), args.get("y1", 0),
                args.get("x2", 0), args.get("y2", 0)
            )
        elif name == "Back":
            return device.press_back()
        elif name == "Home":
            return device.press_home()
        elif name == "Wait":
            time.sleep(args.get("seconds", 1))
            return True
        else:
            return True  # 未知动作默认成功
    
    def _generate_mock_actions(self, max_steps: int) -> list[dict]:
        """生成模拟动作序列"""
        # 使用预定义动作，但不超过 max_steps
        actions = MOCK_ACTIONS[:max_steps]
        return actions
    
    def _get_device(self, device_id: str) -> Device:
        """获取设备"""
        if self.mock or device_id == "mock":
            return self.device_manager.get_mock_device(device_id)
        
        device = self.device_manager.get_device(device_id)
        if not device:
            raise ValueError(f"设备不存在: {device_id}")
        return device
    
    def _load_bundle(self, bundle_path: Path) -> TaskBundle:
        """加载 Task Bundle"""
        task_json = bundle_path / "task.json"
        policy_json = bundle_path / "policy.json"
        system_prompt = bundle_path / "system_prompt.txt"
        user_prompt = bundle_path / "user_task_prompt.txt"
        
        if not task_json.exists():
            raise FileNotFoundError(f"task.json 不存在: {bundle_path}")
        
        from t2p.models.task_bundle import TaskConfig, PolicyConfig
        
        task = TaskConfig.model_validate_json(task_json.read_text())
        policy = PolicyConfig.model_validate_json(policy_json.read_text()) if policy_json.exists() else PolicyConfig()
        
        system = system_prompt.read_text() if system_prompt.exists() else ""
        user = user_prompt.read_text() if user_prompt.exists() else ""
        
        from t2p.models.task_bundle import CompileReport
        
        return TaskBundle(
            spec_id=task.spec_id,
            bundle_id=bundle_path.name,
            task=task,
            policy=policy,
            system_prompt=system,
            user_prompt=user,
            compile_report=CompileReport(
                compiler_version="0.1.0",
                spec_id=task.spec_id,
                input_hash=""
            )
        )
    
    def _load_observation_spec(self, bundle_path: Path) -> ObservationSpec:
        """加载 ObservationSpec"""
        obs_path = bundle_path / "observation_spec.json"
        if obs_path.exists():
            return ObservationSpec.model_validate_json(obs_path.read_text())
        return ObservationSpec(spec_id="unknown")
    
    def _generate_run_id(self, case_id: str) -> str:
        """生成运行 ID"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:6]
        return f"{ts}_{case_id}_{short_uuid}"
    
    def _save_artifact(self, artifact: RunArtifact, run_dir: Path) -> None:
        """保存运行产物"""
        # 保存 meta.json
        meta_path = run_dir / "meta.json"
        meta_path.write_text(artifact.meta.model_dump_json(indent=2))
        
        # 保存 steps.jsonl
        steps_path = run_dir / "steps.jsonl"
        with open(steps_path, "w") as f:
            for step in artifact.steps:
                f.write(step.model_dump_json() + "\n")
        
        # 创建 judge 和 report 目录
        (run_dir / "judge").mkdir(exist_ok=True)
        (run_dir / "report").mkdir(exist_ok=True)
    
    def run_with_agent(
        self,
        bundle_dir: str,
        device_id: str | None = None,
        on_step_callback: callable = None,
        run_id: str | None = None
    ) -> RunArtifact:
        """
        使用 PhoneAgentAdapter 执行 Task Bundle
        
        Args:
            bundle_dir: Task Bundle 目录
            device_id: 设备 ID（可选）
            on_step_callback: 步骤回调函数
            run_id: 指定运行ID（可选，默认自动生成）
            
        Returns:
            RunArtifact
        """
        from runner.executor.phoneagent_adapter import PhoneAgentAdapter
        from runner.models.agent_job import AgentJob, AgentRunStatus
        
        bundle_path = Path(bundle_dir)
        
        # 生成 run_id
        if not run_id:
            run_id = self._generate_run_id(bundle_path.name.replace("_bundle", ""))
        
        # 创建运行目录
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # 从 Bundle 创建 AgentJob
        job = AgentJob.from_bundle(
            bundle_dir=str(bundle_path),
            job_id=run_id,
            workspace_dir=str(run_dir),
            api_key=self.api_key,
            device_id=device_id
        )
        
        # 初始化 Adapter
        self.adapter = PhoneAgentAdapter(mock=self.mock, on_step=on_step_callback)
        adapter = self.adapter
        
        if self.verbose:
            print(f"[Runner] 使用 PhoneAgentAdapter 执行")
            print(f"[Runner] Job ID: {job.job_id}")
            print(f"[Runner] Mock: {self.mock}")
        
        # 执行
        result = self.adapter.run(job)
        
        if self.verbose:
            print(f"[Runner] 执行完成: {result.status.value}")
            print(f"[Runner] 步数: {result.step_count}")
        
        # 转换为 RunArtifact
        observation_spec = self._load_observation_spec(bundle_path)
        
        # 确定状态
        status_map = {
            AgentRunStatus.FINISHED: RunStatus.PASS,
            AgentRunStatus.TIMEOUT: RunStatus.TIMEOUT,
            AgentRunStatus.BLOCKED: RunStatus.BLOCKED,
            AgentRunStatus.ERROR: RunStatus.ERROR,
        }
        
        artifact = RunArtifact(
            meta=RunMeta(
                run_id=run_id,
                case_id=job.job_id,
                bundle_id=bundle_path.name,
                device_id=device_id or "mock",
                device_type=job.device.device_type,
                max_steps=job.run.max_steps,
                timeout_sec=job.run.timeout_sec,
                started_at=datetime.now(),
                status=status_map.get(result.status, RunStatus.ERROR),
                exit_reason=result.exit_reason,
                duration_sec=result.duration_sec
            ),
            artifact_dir=str(run_dir),
            evidence_dir=str(run_dir / "evidence")
        )
        
        artifact.meta.finished_at = datetime.now()
        
        # 如果有 guard 违规，添加事件
        if result.guard_violations:
            from runner.models.run_artifact import EventRecord
            for guard in result.guard_violations:
                artifact.events.append(EventRecord(
                    event="guard_violation",
                    reason=guard
                ))
        
        # 保存 artifact（meta 已由 adapter 保存，这里更新）
        self._save_artifact(artifact, run_dir)
        
        return artifact
