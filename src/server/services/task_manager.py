import asyncio
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from fastapi import WebSocket

from runner.executor.runner import TaskRunner
from runner.models.run_artifact import RunArtifact

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, list[WebSocket]] = {}
    
    async def connect(self, run_id: str, websocket: WebSocket):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)
        
    def disconnect(self, run_id: str, websocket: WebSocket):
        if run_id in self.active_connections:
            self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
                
    async def broadcast(self, run_id: str, message: dict):
        if run_id in self.active_connections:
            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to websocket: {e}")

manager = ConnectionManager()

class TaskManager:
    def __init__(self):
        self._runs: Dict[str, Any] = {}
        self._active_runners: Dict[str, Any] = {} # active runners
        self._load_history()

    def _load_history(self):
        """从磁盘加载历史任务"""
        import os
        import json
        runs_dir = "runs"
        if not os.path.exists(runs_dir):
            return
            
        for run_id in os.listdir(runs_dir):
            meta_path = os.path.join(runs_dir, run_id, "run_meta.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        self._runs[run_id] = meta
                except Exception as e:
                    logger.warning(f"Failed to load run {run_id}: {e}")

    def list_runs(self) -> List[Dict[str, Any]]:
        """获取任务列表"""
        return list(self._runs.values())

    async def create_run(self, doc_id: str, device_id: str, config: dict) -> str:
        """创建并启动任务"""
        import os
        import json
        
        run_id = f"web_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        run_data = {
            "id": run_id,
            "doc_id": doc_id,
            "device_id": device_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "logs": [],
            "config": config
        }
        
        self._runs[run_id] = run_data
        
        # Persist initial metadata
        os.makedirs(os.path.join("runs", run_id), exist_ok=True)
        with open(os.path.join("runs", run_id, "run_meta.json"), "w", encoding="utf-8") as f:
            json.dump(run_data, f, ensure_ascii=False, indent=2)
        
        # 异步启动
        asyncio.create_task(self._run_task(run_id, doc_id, device_id, config))
        
        return run_id
        
    async def _update_status(self, run_id: str, status: str):
        if run_id in self._runs:
            self._runs[run_id]["status"] = status
            # Update disk
            import os
            import json
            meta_path = os.path.join("runs", run_id, "run_meta.json")
            try:
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(self._runs[run_id], f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Failed to save meta for {run_id}: {e}")

    def _compile_task_sync(self, run_id: str, doc_path: str, log_callback: callable) -> str:
        """同步执行编译逻辑（Doc2Spec + T2P）"""
        import os
        from pathlib import Path
        
        log_callback(f"开始处理文档: {os.path.basename(doc_path)}")
        
        if doc_path.endswith("_bundle"):
            log_callback(f"使用已有 Bundle: {doc_path}")
            return doc_path
            
        log_callback("开始编译 TestSpec (Doc2Spec)...")
        
        try:
            # 1.1 Doc -> TestSpec
            from doc2spec.modules.normalize import Normalizer
            from doc2spec.modules.mine import RequirementMiner
            from doc2spec.modules.synth import SpecSynthesizer
            from doc2spec.modules.lint import lint_specs
            from doc2spec.cli import get_adapter
            from doc2spec.config import get_config
            
            config_d2s = get_config()
            use_dummy = not config_d2s.llm.api_key
            if use_dummy:
                log_callback("警告: Doc2Spec 未配置 API Key，将使用 Dummy 模式")
            
            normalizer = Normalizer()
            docs = [normalizer.normalize_file(Path(doc_path))]
            
            log_callback("正在分析文档需求...")
            adapter = get_adapter(use_dummy=use_dummy)
            miner = RequirementMiner(adapter=adapter)
            batches = miner.mine_from_docs(docs)
            
            log_callback("正在生成测试规格...")
            synthesizer = SpecSynthesizer(adapter=adapter, use_llm=not use_dummy)
            specs = synthesizer.synthesize_from_batches(batches)
            
            if not specs:
                raise ValueError("未生成任何 TestSpec")
                
            valid_specs, _ = lint_specs(specs, auto_fix=True)
            if not valid_specs:
                raise ValueError("TestSpec 校验失败")
            
            spec = valid_specs[0]
            log_callback(f"生成的 TestSpec: {spec.id}")
            
            # 1.2 TestSpec -> Bundle (T2P)
            log_callback("开始编译 Bundle (T2P)...")
            from t2p.compiler.packager import T2PCompiler, Packager
            
            bundle_output_dir = Path("runs") / run_id / "bundle_out"
            bundle_output_dir.mkdir(parents=True, exist_ok=True)
            
            compiler = T2PCompiler(lang="cn", strict=False)
            packager = Packager(output_dir=bundle_output_dir)
            
            t2p_bundle, obs_spec = compiler.compile(spec)
            bundle_dir = packager.package(t2p_bundle, obs_spec)
            
            bundle_path = str(bundle_dir)
            log_callback(f"Bundle 编译完成: {bundle_path}")
            return bundle_path
            
        except Exception as e:
            logger.error(f"Compilation failed for {run_id}: {e}", exc_info=True)
            log_callback(f"编译失败: {str(e)}")
            raise e

    async def _run_task(self, run_id: str, doc_id: str, device_id: str, config: dict):
        await self._update_status(run_id, "running")
        await manager.broadcast(run_id, {"type": "status", "status": "running"})
        
        try:
            import os
            from pathlib import Path
            from runner.executor.runner import TaskRunner
            
            # 1. 编译 (Doc -> Bundle)
            doc_path = f"uploads/{doc_id}"
            if not os.path.exists(doc_path) and os.path.exists(doc_id):
                  doc_path = doc_id
            
            main_loop = asyncio.get_running_loop()
            
            def log_callback(msg):
                asyncio.run_coroutine_threadsafe(self._log(run_id, msg), main_loop)

            # Offload compilation to thread to avoid blocking the event loop
            try:
                bundle_path = await asyncio.to_thread(
                    self._compile_task_sync, 
                    run_id, 
                    doc_path, 
                    log_callback
                )
            except Exception as e:
                # Error already logged inside _compile_task_sync
                raise e

            # 2. 执行 Runner
            api_key = os.getenv("ZHIPU_API_KEY")
            
            # Ensure Runner uses the correct runs_dir (our web runs dir)
            runner = TaskRunner(runs_dir="runs", mock=False, api_key=api_key, use_agent=True)
            self._active_runners[run_id] = runner
            
            # 定义回调
            def on_step(step_data: dict):
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(run_id, {"type": "step", "data": step_data}),
                    main_loop
                )
                if "action" in step_data:
                    action_name = step_data["action"].get("name")
                    asyncio.run_coroutine_threadsafe(
                        self._log(run_id, f"执行步骤: {action_name}"),
                        main_loop
                    )
                    
                    # 检查 Takeover
                    if action_name == "Take_over":
                        args_raw = step_data["action"].get("args_raw", "")
                        message = "Agent 请求人工接管"
                        asyncio.run_coroutine_threadsafe(
                             manager.broadcast(run_id, {
                                 "type": "takeover_request", 
                                 "message": args_raw or message
                             }),
                             main_loop
                        )
                # LIVE VIEW: Steady Event-driven Way
                try:
                    if "screen" in step_data and step_data["screen"]:
                        rel_path = step_data["screen"]
                        # The URL for frontend to fetch the screenshot
                        screenshot_url = f"/artifacts/{run_id}/{rel_path}"
                        asyncio.run_coroutine_threadsafe(
                             manager.broadcast(run_id, {
                                 "type": "live_update", 
                                 "url": screenshot_url
                             }),
                             main_loop
                        )
                except Exception as e:
                    logger.warning(f"Failed to send live update: {e}")

            await self._log(run_id, f"启动 TaskRunner (Device: {device_id})...")
            
            def run_sync():
                return runner.run_with_agent(
                    bundle_dir=bundle_path,
                    device_id=device_id if device_id != "mock" else None,
                    on_step_callback=on_step,
                    run_id=run_id
                )
            
            artifact = await asyncio.to_thread(run_sync)
            
            # Check if it was stopped
            final_status = self._runs[run_id].get("status")
            if final_status != "stopped":
                # Update meta with artifact info
                self._runs[run_id]["artifact_path"] = str(artifact.artifact_dir)
                await self._update_status(run_id, "done")
                await manager.broadcast(run_id, {"type": "status", "status": "done"})
            
        except asyncio.CancelledError:
             logger.info(f"Run {run_id} cancelled (asyncio)")
             if self._runs[run_id].get("status") != "stopped":
                 await self._log(run_id, "任务被取消")
                 await self._update_status(run_id, "stopped")
                 await manager.broadcast(run_id, {"type": "status", "status": "stopped"})
            
        except Exception as e:
            logger.error(f"Run failed: {e}", exc_info=True)
            await self._log(run_id, f"错误: {str(e)}")
            await self._update_status(run_id, "failed")
            await manager.broadcast(run_id, {"type": "status", "status": "failed"})
        finally:
            if run_id in self._active_runners:
                del self._active_runners[run_id]

    async def _log(self, run_id: str, content: str):
        entry = {"ts": datetime.now().isoformat(), "content": content}
        if run_id in self._runs:
            self._runs[run_id]["logs"].append(entry)
        await manager.broadcast(run_id, {"type": "log", "content": content})

    def get_run(self, run_id: str):
        return self._runs.get(run_id)

    async def stop_run(self, run_id: str):
        """停止任务"""
        if run_id in self._runs and self._runs[run_id]["status"] == "running":
            # 1. 立即标记状态并广播
            await self._update_status(run_id, "stopped")
            await self._log(run_id, "用户请求停止任务")
            await manager.broadcast(run_id, {"type": "status", "status": "stopped"})
            
            # 2. 调用 Runner 的停止方法
            if run_id in self._active_runners:
                runner = self._active_runners[run_id]
                logger.info(f"Stopping runner for {run_id}")
                runner.stop()
            return True
        return False

task_manager = TaskManager()
