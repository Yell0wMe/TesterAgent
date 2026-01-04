"""
PhoneAgent Adapter - PhoneAgent 交互适配器

这是系统与 PhoneAgent 交互的唯一入口。
支持 CLI 子进程调用和 Mock 模式。
"""

import os
import sys
import json
import time
import subprocess
import re
import signal
from pathlib import Path
from datetime import datetime
from typing import Generator

from runner.models.agent_job import AgentJob, AgentRunResult, AgentRunStatus


# Guard 关键词（硬拦截）
GUARD_KEYWORDS = {
    "real_payment": ["支付", "付款", "下单", "确认支付", "购买", "pay", "checkout"],
    "account_deletion": ["删除账号", "注销", "注销账号", "delete account"],
    "unbind_bankcard": ["解绑银行卡", "解绑卡", "unbind card"],
    "send_message": ["发送", "发布", "转发", "私信", "发消息", "send", "post"],
}

# Takeover 关键词
TAKEOVER_KEYWORDS = ["验证码", "captcha", "登录密码", "短信验证", "人脸识别", "指纹"]


class PhoneAgentAdapter:
    """
    PhoneAgent 适配器
    
    支持两种模式：
    1. CLI 模式：调用 Open-AutoGLM 命令行
    2. Mock 模式：模拟执行（用于测试和无设备环境）
    """
    
    def __init__(
        self,
        autoglm_path: str | None = None,
        mock: bool = False,
        on_step: callable = None
    ):
        """
        初始化
        
        Args:
            autoglm_path: Open-AutoGLM 路径（默认 vendor/open-autoglm）
            mock: 是否使用 Mock 模式
            on_step: 步骤回调函数
        """
        self.autoglm_path = autoglm_path or "vendor/open-autoglm"
        self.mock = mock
        self.on_step = on_step
        self._process = None # Track process

    def stop(self):
        """停止任务进程"""
        if self._process and self._process.poll() is None:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Terminating PhoneAgent process group {self._process.pid}")
            try:
                # 杀掉整个进程组 (start_new_session=True 开启了新会话/进程组)
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                
                # 等待一会儿，如果还没死就 SIGKILL
                start_wait = time.time()
                while time.time() - start_wait < 5:
                    if self._process.poll() is not None:
                        break
                    time.sleep(0.5)
                
                if self._process.poll() is None:
                    logger.warning(f"Process {self._process.pid} did not terminate, killing it group")
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
            except Exception as e:
                logger.error(f"Error stopping process: {e}")
                # Fallback to direct kill if killpg fails
                try:
                    self._process.kill()
                except:
                    pass
    
    def run(self, job: AgentJob) -> AgentRunResult:
        """
        执行 AgentJob
        
        Args:
            job: AgentJob 任务
            
        Returns:
            AgentRunResult 执行结果
        """
        workspace = Path(job.workspace_dir)
        workspace.mkdir(parents=True, exist_ok=True)
        
        # 创建目录结构
        screenshots_dir = workspace / "evidence" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        logs_dir = workspace / "evidence" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 路径
        steps_path = workspace / "steps.jsonl"
        verbose_log_path = workspace / "agent_verbose.log"
        meta_path = workspace / "meta.json"
        actions_path = workspace / "repro" / "actions.json"
        actions_path.parent.mkdir(exist_ok=True)
        
        start_time = time.time()
        
        if self.mock:
            result = self._run_mock(job, workspace, screenshots_dir)
        else:
            result = self._run_cli(job, workspace, screenshots_dir, verbose_log_path)
        
        # 计算耗时
        result.duration_sec = time.time() - start_time
        
        # 保存 meta
        self._save_meta(job, result, meta_path)
        
        return result
    
    def _run_mock(
        self,
        job: AgentJob,
        workspace: Path,
        screenshots_dir: Path
    ) -> AgentRunResult:
        """Mock 模式执行"""
        steps = []
        guard_violations = []
        takeover = False
        status = AgentRunStatus.FINISHED
        exit_reason = None
        
        # 模拟执行步骤
        mock_actions = [
            {"name": "Launch", "args": {"package": "目标应用"}},
            {"name": "Wait", "args": {"seconds": 1}},
            {"name": "Tap", "args": {"target": "登录按钮"}},
            {"name": "Type", "args": {"text": "用户名"}},
            {"name": "Tap", "args": {"target": "确认"}},
        ]
        
        max_steps = min(job.run.max_steps, len(mock_actions))
        
        for i, action in enumerate(mock_actions[:max_steps]):
            # 检查 Guards
            violation = self._check_guards(action, job.policy.guards)
            if violation:
                guard_violations.append(violation)
                status = AgentRunStatus.BLOCKED
                exit_reason = f"guard_violation:{violation}"
                break
            
            # 检查 Takeover
            if self._check_takeover(action):
                takeover = True
                status = AgentRunStatus.BLOCKED
                exit_reason = "takeover_required"
                break
            
            # 记录步骤
            step = {
                "i": i,
                "ts": datetime.now().isoformat(),
                "action": action,
                "screen": f"evidence/screenshots/step_{i:03d}.png",
                "status": "ok",
                "latency_ms": 100
            }
            steps.append(step)
            
            # 生成模拟截图
            self._create_mock_screenshot(screenshots_dir / f"step_{i:03d}.png")
            
            # 回调
            if self.on_step:
                self.on_step(step)
            
            time.sleep(0.05)  # 模拟延迟
        
        # 最终截图
        final_path = screenshots_dir / "final.png"
        self._create_mock_screenshot(final_path)
        
        # 写 steps.jsonl
        steps_path = workspace / "steps.jsonl"
        with open(steps_path, "w") as f:
            for step in steps:
                f.write(json.dumps(step, ensure_ascii=False) + "\n")
        
        # 写 verbose log
        verbose_path = workspace / "agent_verbose.log"
        verbose_path.write_text(f"[Mock] 执行了 {len(steps)} 个步骤\n")
        
        # 写 actions.json
        actions_path = workspace / "repro" / "actions.json"
        actions_path.write_text(json.dumps(
            [s["action"] for s in steps],
            ensure_ascii=False,
            indent=2
        ))
        
        return AgentRunResult(
            job_id=job.job_id,
            status=status,
            exit_reason=exit_reason,
            steps_jsonl_path=str(steps_path),
            screenshots_dir=str(screenshots_dir),
            final_screenshot_path=str(final_path),
            agent_verbose_log_path=str(verbose_path),
            repro_actions_path=str(actions_path),
            meta_path=str(workspace / "meta.json"),
            step_count=len(steps),
            guard_violations=guard_violations,
            takeover_triggered=takeover
        )
    
    def _run_cli(
        self,
        job: AgentJob,
        workspace: Path,
        screenshots_dir: Path,
        verbose_log_path: Path
    ) -> AgentRunResult:
        """CLI 模式执行"""
        # 构建命令
        cmd = self._build_command(job)
        
        steps = []
        guard_violations = []
        status = AgentRunStatus.FINISHED
        exit_reason = None
        
        try:
            # 执行命令
            with open(verbose_log_path, "w") as log_file:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=self.autoglm_path,
                    start_new_session=True
                )
                process = self._process
                
                step_index = 0
                start_time = time.time()
                
                for line in process.stdout:
                    # 写入日志
                    log_file.write(line)
                    log_file.flush()
                    
                    # 解析动作
                    action = self._parse_action_from_log(line)
                    if action:
                        # 检查 Guards
                        violation = self._check_guards(action, job.policy.guards)
                        if violation:
                            guard_violations.append(violation)
                            process.terminate()
                            status = AgentRunStatus.BLOCKED
                            exit_reason = f"guard_violation:{violation}"
                            break
                        
                        # 记录步骤
                        step = {
                            "i": step_index,
                            "ts": datetime.now().isoformat(),
                            "action": action,
                            "status": "ok"
                        }
                        
                        # 采集截图
                        if job.evidence_plan.screenshot_each_step:
                            screenshot_path = screenshots_dir / f"step_{step_index:03d}.png"
                            self._capture_screenshot(job.device, screenshot_path)
                            # Store relative path for frontend compatibility
                            step["screen"] = f"evidence/screenshots/step_{step_index:03d}.png"
                            
                        # Callback
                        if self.on_step:
                            self.on_step(step)

                        steps.append(step)
                        step_index += 1
                    
                    # 检查超时
                    if time.time() - start_time > job.run.timeout_sec:
                        process.terminate()
                        status = AgentRunStatus.TIMEOUT
                        exit_reason = f"timeout:{job.run.timeout_sec}s"
                        break
                
                process.wait()
        
        except Exception as e:
            status = AgentRunStatus.ERROR
            exit_reason = str(e)
        
        # 写 steps.jsonl
        steps_path = workspace / "steps.jsonl"
        with open(steps_path, "w") as f:
            for step in steps:
                f.write(json.dumps(step, ensure_ascii=False) + "\n")
        
        # 查找最终截图
        final_path = screenshots_dir / "final.png"
        if not final_path.exists():
            # 使用最后一个步骤截图
            step_screenshots = sorted(screenshots_dir.glob("step_*.png"))
            if step_screenshots:
                import shutil
                shutil.copy(step_screenshots[-1], final_path)
        
        return AgentRunResult(
            job_id=job.job_id,
            status=status,
            exit_reason=exit_reason,
            steps_jsonl_path=str(steps_path),
            screenshots_dir=str(screenshots_dir),
            final_screenshot_path=str(final_path) if final_path.exists() else None,
            agent_verbose_log_path=str(verbose_log_path),
            meta_path=str(workspace / "meta.json"),
            step_count=len(steps),
            guard_violations=guard_violations
        )
    
    def _build_command(self, job: AgentJob) -> list[str]:
        """构建 CLI 命令"""
        cmd = [
            sys.executable, "main.py",
            "--base-url", job.model.base_url,
            "--model", job.model.model_name,
            "--apikey", job.model.api_key,
            "--device-type", job.device.device_type,
            "--max-steps", str(job.run.max_steps),
            "--lang", job.run.lang,
        ]
        
        if job.device.device_id:
            cmd.extend(["--device-id", job.device.device_id])
        
        # if job.run.verbose:
        #     cmd.append("--verbose")
        
        # 任务文本作为最后参数
        cmd.append(job.task_text)
        
        return cmd
    
    def _parse_action_from_log(self, line: str) -> dict | None:
        """从日志行解析动作"""
        # 尝试匹配常见的动作格式
        # 1. Parsing action: do(action="Launch", app="微信")
        # 2. Parsing action: finish(message="...")
        
        # 匹配 Parsing action: do(...)
        do_match = re.search(r'Parsing action: do\(action="(\w+)"(?:,\s*(.*))?\)', line)
        if do_match:
            action_name = do_match.group(1)
            args_str = do_match.group(2) or ""
            return {"name": action_name, "args_raw": args_str}
            
        # 匹配 Parsing action: finish(...) 
        finish_match = re.search(r'Parsing action: finish\(', line)
        if finish_match:
            return {"name": "Finish", "args_raw": line}

        # 旧格式兼容
        patterns = [
            r"(?:Action|动作)[:\s]+(\w+)\(([^)]*)\)",
            r"执行[:\s]+(\w+)\s+(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                action_name = match.group(1)
                args_str = match.group(2)
                return {"name": action_name, "args_raw": args_str}
        
        return None
    
    def _check_guards(self, action: dict, guards: list[str]) -> str | None:
        """检查是否触发 Guards"""
        action_str = json.dumps(action, ensure_ascii=False).lower()
        
        for guard in guards:
            keywords = GUARD_KEYWORDS.get(guard, [guard])
            for keyword in keywords:
                if keyword.lower() in action_str:
                    return guard
        
        return None
    
    def _check_takeover(self, action: dict) -> bool:
        """检查是否需要 Takeover"""
        action_str = json.dumps(action, ensure_ascii=False)
        
        for keyword in TAKEOVER_KEYWORDS:
            if keyword in action_str:
                return True
        
        return False
    
    def _create_mock_screenshot(self, path: Path) -> None:
        """创建模拟截图"""
        # 最小 PNG 文件（1x1 透明像素）
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
            0x42, 0x60, 0x82
        ])
        with open(path, "wb") as f:
            f.write(png_data)
    
    def _capture_screenshot(self, device_config, path: Path) -> None:
        """采集设备截图"""
        try:
            device_id = device_config.device_id
            cmd = ["adb"]
            if device_id:
                cmd.extend(["-s", device_id])
            cmd.extend(["exec-out", "screencap", "-p"])
            
            with open(path, "wb") as f:
                subprocess.run(cmd, stdout=f, check=True)
        except Exception as e:
            print(f"[警告] 截图失败: {e}")

    def _save_meta(self, job: AgentJob, result: AgentRunResult, meta_path: Path) -> None:
        """保存执行元数据"""
        meta = {
            "job_id": job.job_id,
            "status": result.status.value,
            "exit_reason": result.exit_reason,
            "model": {
                "base_url": job.model.base_url,
                "model_name": job.model.model_name
            },
            "device": {
                "type": job.device.device_type,
                "id": job.device.device_id
            },
            "run": {
                "max_steps": job.run.max_steps,
                "timeout_sec": job.run.timeout_sec,
                "lang": job.run.lang
            },
            "result": {
                "step_count": result.step_count,
                "duration_sec": result.duration_sec,
                "guard_violations": result.guard_violations,
                "takeover_triggered": result.takeover_triggered
            },
            "executed_at": datetime.now().isoformat()
        }
        
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
