"""
AgentJob 数据模型

定义 PhoneAgent 执行任务的输入输出结构。
"""

from typing import Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """模型配置"""
    base_url: str = Field(default="https://open.bigmodel.cn/api/paas/v4/")
    model_name: str = Field(default="autoglm-phone")
    api_key: str = Field(default="")


class DeviceConfig(BaseModel):
    """设备配置"""
    device_type: str = Field(default="adb", description="adb 或 hdc")
    device_id: str | None = Field(default=None, description="设备 ID")


class RunConfig(BaseModel):
    """运行配置"""
    lang: str = Field(default="zh", description="语言 zh/en")
    max_steps: int = Field(default=40, description="最大步骤数")
    timeout_sec: int = Field(default=180, description="超时秒数")
    verbose: bool = Field(default=True, description="详细输出")


class PolicyConfig(BaseModel):
    """策略配置"""
    guards: list[str] = Field(default_factory=list, description="禁止操作列表")
    takeover_hints: list[str] = Field(default_factory=list, description="接管提示词")


class EvidencePlan(BaseModel):
    """证据采集计划"""
    screenshot_each_step: bool = Field(default=True)
    screenshot_final: bool = Field(default=True)
    screenshot_on_assertions: bool = Field(default=True)
    logcat_on_error: bool = Field(default=True)


class AgentJob(BaseModel):
    """
    AgentJob - PhoneAgent 执行任务
    
    这是系统与 PhoneAgent 交互的唯一输入结构。
    来自第2层 T2P 编译产物。
    """
    job_id: str
    task_text: str = Field(..., description="测试员任务提示词（来自第2层编译）")
    
    model: ModelConfig = Field(default_factory=ModelConfig)
    device: DeviceConfig = Field(default_factory=DeviceConfig)
    run: RunConfig = Field(default_factory=RunConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    
    observation_spec: dict = Field(default_factory=dict, description="断言→观察任务")
    evidence_plan: EvidencePlan = Field(default_factory=EvidencePlan)
    
    workspace_dir: str = Field(..., description="本次运行产物目录")
    
    @classmethod
    def from_bundle(
        cls,
        bundle_dir: str,
        job_id: str,
        workspace_dir: str,
        api_key: str = "",
        device_id: str | None = None
    ) -> "AgentJob":
        """从 Task Bundle 创建 AgentJob"""
        import json
        from pathlib import Path
        
        bundle_path = Path(bundle_dir)
        
        # 读取任务提示词
        user_prompt_path = bundle_path / "user_task_prompt.txt"
        system_prompt_path = bundle_path / "system_prompt.txt"
        
        task_text = ""
        if system_prompt_path.exists():
            task_text += system_prompt_path.read_text() + "\n\n"
        if user_prompt_path.exists():
            task_text += user_prompt_path.read_text()
        
        # 读取 policy
        policy_path = bundle_path / "policy.json"
        policy_data = {}
        if policy_path.exists():
            policy_data = json.loads(policy_path.read_text())
        
        guards = [g.get("name", "") for g in policy_data.get("guards", [])]
        
        # 读取 observation_spec
        obs_path = bundle_path / "observation_spec.json"
        obs_spec = {}
        if obs_path.exists():
            obs_spec = json.loads(obs_path.read_text())
        
        # 读取 task.json 获取配置
        task_path = bundle_path / "task.json"
        task_data = {}
        if task_path.exists():
            task_data = json.loads(task_path.read_text())
        
        agent_config = task_data.get("agent_config", {})
        
        return cls(
            job_id=job_id,
            task_text=task_text,
            model=ModelConfig(api_key=api_key),
            device=DeviceConfig(device_id=device_id),
            run=RunConfig(
                max_steps=agent_config.get("max_steps", 40),
                lang=agent_config.get("lang", "zh")
            ),
            policy=PolicyConfig(guards=guards),
            observation_spec=obs_spec,
            workspace_dir=workspace_dir
        )


class AgentRunStatus(str, Enum):
    """运行状态"""
    FINISHED = "finished"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    ERROR = "error"


class AgentRunResult(BaseModel):
    """
    AgentRunResult - PhoneAgent 执行结果
    
    这是系统与 PhoneAgent 交互的唯一输出结构。
    给 Judge 用于判定。
    """
    job_id: str
    status: AgentRunStatus
    exit_reason: str | None = None
    
    # 产物路径
    steps_jsonl_path: str
    screenshots_dir: str
    final_screenshot_path: str | None = None
    agent_verbose_log_path: str
    repro_actions_path: str | None = None
    meta_path: str
    
    # 统计
    step_count: int = 0
    duration_sec: float = 0.0
    guard_violations: list[str] = Field(default_factory=list)
    takeover_triggered: bool = False
