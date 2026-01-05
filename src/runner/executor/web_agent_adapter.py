import json
import time
import base64
import re
from pathlib import Path
from datetime import datetime
from zhipuai import ZhipuAI
from runner.models.agent_job import AgentJob, AgentRunResult, AgentRunStatus

# Guard 关键词（硬拦截）
GUARD_KEYWORDS = {
    "real_payment": ["支付", "付款", "下单", "确认支付", "购买", "pay", "checkout"],
    "account_deletion": ["删除账号", "注销", "注销账号", "delete account"],
    "unbind_bankcard": ["解绑银行卡", "解绑卡", "unbind card"],
    "send_message": ["发送", "发布", "转发", "私信", "发消息", "send", "post"],
}

# Takeover 关键词
TAKEOVER_KEYWORDS = ["验证码", "captcha", "登录密码", "短信验证", "人脸识别", "指纹", "滑块验证"]


class WebAgentAdapter:
    """
    Web Agent Adapter using GLM-4V / AutoGLM-Web Logic.
    Directly interacts with ZhipuAI API to drive the WebDevice.
    Supports full TestSpec execution with guards, takeover, and observation_spec.
    """
    
    def __init__(self, api_key: str, mock: bool = False, on_step: callable = None):
        self.client = ZhipuAI(api_key=api_key)
        self.mock = mock
        self.on_step = on_step
        self.model = "glm-4v"
        self.guard_violations = []
        self.takeover_triggered = False
        self._stop_requested = False
        self._device = None  # Store device reference for cleanup

    def stop(self):
        """Request stop of the running agent"""
        print("[WebAgent] Stop requested")
        self._stop_requested = True
        if self._device:
            try:
                self._device.disconnect()
            except:
                pass

    def run(self, job: AgentJob) -> AgentRunResult:
        workspace = Path(job.workspace_dir)
        workspace.mkdir(parents=True, exist_ok=True)
        
        screenshots_dir = workspace / "evidence" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        steps = []
        status = AgentRunStatus.FINISHED
        exit_reason = "finished"
        
        # WebDevice instance should be passed or retrieved. 
        # In current runner architecture, job.device is config, runner has the instance.
        # But wait, PhoneAgentAdapter spawns a process, handling device internally or via CLI args.
        # WebAgentAdapter runs in-process. The Runner calls `adapter.run(job)`.
        # Problem: `adapter.run` doesn't receive the `Device` object, only `job` config.
        # Solution: I need to instantiate the WebDevice here if it's not passed.
        # However, `WebRunner` (which I didn't create, I modified `runner.py`) uses `_get_device`.
        # The `runner.py` logic:
        # runner.run_with_agent -> adapter.run(job)
        # So adapter is responsible for controlling the device.
        
        # Instantiate WebDevice based on job config
        # Start in VISIBLE mode so user can interact for login
        from runner.web.device import WebDevice
        device = WebDevice(headless=False)  # Visible mode for takeover
        self._device = device  # Store for stop()
        
        try:
            # 0. Initial Launch (Auto-Navigate)
            # Extract URL from task text to ensure we start on the right page
            # 0. Initial Launch (Auto-Navigate)
            # Extract URL from task text to ensure we start on the right page
            url_match = re.search(r'(?:https?://|www\.)[^\s"\']+', job.task_text)
            if url_match:
                start_url = url_match.group(0)
                if start_url.startswith("www."):
                    start_url = "https://" + start_url
                print(f"[WebAgent] Auto-launching URL: {start_url}")
                device._driver.execute("navigate", {"url": start_url})
                time.sleep(3) # Wait for load
            
            history = []
            
            for i in range(job.run.max_steps):
                # Check stop flag at start of each loop
                if self._stop_requested:
                    print("[WebAgent] Stop flag detected, exiting loop")
                    status = AgentRunStatus.BLOCKED
                    exit_reason = "User stopped"
                    break
                # 1. Capture State
                time.sleep(2) # Give browser time to settle before screenshot/DOM
                screen_path = screenshots_dir / f"step_{i:03d}.png"
                device.screenshot(str(screen_path))
                
                # Encode Image
                with open(screen_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode('utf-8')
                
                # Get DOM (simplified)
                try:
                    dom_res = device._driver.execute("get_dom", {})
                    dom_tree = dom_res.get("dom", {})
                except:
                    dom_tree = {}
                
                # Check for login page (Takeover detection)
                # Improved detection: only trigger if BOTH keywords AND password/input role present
                page_content = json.dumps(dom_tree, ensure_ascii=False).lower()
                login_keywords = ["登录", "登陆", "login", "signin", "账号", "注册"]
                
                # Check for password field or sensitive inputs
                has_password_input = 'password' in page_content or '密码' in page_content or '"role": "password"' in page_content
                
                needs_login = False
                # If we see password field AND login keywords, it's likely a login page
                if has_password_input and any(kw in page_content for kw in login_keywords):
                    needs_login = True
                
                # Also check page title/URL for explicit login signals
                try:
                    page_url = device._driver.execute("get_url", {}).get("url", "").lower()
                    page_title = device._driver.execute("get_title", {}).get("title", "").lower()
                    if any(kw in page_url for kw in ["/login", "/signin", "/auth"]) and \
                       any(kw in page_title for kw in login_keywords):
                        needs_login = True
                except:
                    pass
                
                if needs_login and not getattr(self, '_login_completed', False):
                    print(f"[WebAgent] Step {i}: Login page detected. URL: {page_url if 'page_url' in locals() else 'unknown'}")
                    self.takeover_triggered = True
                    
                    # Notify via callback
                    if self.on_step:
                        self.on_step({
                            "i": i,
                            "ts": datetime.now().isoformat(),
                            "action": {"name": "Takeover", "args": {"reason": "Login Required"}},
                            "screen": f"evidence/screenshots/step_{i:03d}.png",
                            "status": "takeover",
                            "error": "检测到登录页面，请在弹出的浏览器中完成登录以继续..."
                        })
                    
                    # Wait for user to complete login (poll every 5 seconds to reduce flicker/load)
                    login_wait_timeout = 300  # 5 minutes max
                    login_start = time.time()
                    
                    while time.time() - login_start < login_wait_timeout:
                        if self._stop_requested:
                            print("[WebAgent] Stop requested during login wait")
                            status = AgentRunStatus.BLOCKED
                            exit_reason = "User stopped during login"
                            break
                        
                        time.sleep(5)
                        
                        # Check if still on login page
                        try:
                            # Use simple URL/Title check first to avoid heavy DOM snapshot
                            new_url = device._driver.execute("get_url", {}).get("url", "").lower()
                            new_title = device._driver.execute("get_title", {}).get("title", "").lower()
                            
                            # Log progress
                            print(f"[WebAgent] Still waiting for login... Current URL: {new_url}")
                            
                            # If URL changed significantly and doesn't contain login keywords
                            is_still_login_url = any(kw in new_url for kw in ["login", "signin", "auth"])
                            
                            if not is_still_login_url:
                                # Double check DOM only if URL looks safe
                                new_dom = device._driver.execute("get_dom", {}).get("dom", {})
                                new_content = json.dumps(new_dom, ensure_ascii=False).lower()
                                still_has_password = 'password' in new_content or '密码' in new_content
                                
                                if not still_has_password:
                                    print("[WebAgent] Login seems completed! Continuing...")
                                    self._login_completed = True
                                    
                                    # Take post-login screenshot
                                    post_login_path = screenshots_dir / f"step_{i:03d}_post_login.png"
                                    device.screenshot(str(post_login_path))
                                    
                                    if self.on_step:
                                        self.on_step({
                                            "i": i,
                                            "ts": datetime.now().isoformat(),
                                            "action": {"name": "LoginComplete", "args": {}},
                                            "screen": f"evidence/screenshots/step_{i:03d}_post_login.png",
                                            "status": "success",
                                            "error": "登录完成，继续任务"
                                        })
                                    break
                        except Exception as e:
                            print(f"[WebAgent] Error checking login status: {e}")
                    else:
                        # Timeout
                        print("[WebAgent] Login timeout")
                        status = AgentRunStatus.TIMEOUT
                        exit_reason = "Login timeout"
                        break
                    
                    if self._stop_requested or status == AgentRunStatus.TIMEOUT:
                        break
                    
                    continue
                
                # 2. Query LLM
                if self.on_step:
                     self.on_step({"i": i, "status": "thinking", "error": "Agent 正在思考下一步操作..."})
                     
                prompt = self._build_prompt(job.task_text, dom_tree, i)
                
                # Add image to history or current message
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT.format(width=1280, height=720)},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": img_b64}}
                    ]}
                ]
                
                # Add simple history (last 5 actions)
                if history:
                    hist_text = "Action History:\n" + "\n".join([
                        f"- Step {h['i']}: {h['action']} -> {h['status']} {f'({h['error']})' if h.get('error') else ''}" 
                        for h in history[-5:]
                    ])
                    messages[0]["content"] += "\n\n" + hist_text

                print(f"[WebAgent] Step {i}: Querying GLM-4V...")
                
                # Retry Loop
                content = None
                for attempt in range(3):
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=0.1,
                            max_tokens=1024
                        )
                        content = response.choices[0].message.content
                        if content:
                            break
                    except Exception as e:
                        print(f"[WebAgent] LLM Attempt {attempt+1} Error: {e}")
                        time.sleep(2)
                
                if not content:
                    print("[WebAgent] Failed to get response after 3 attempts.")
                    break
                    
                print(f"[WebAgent] Response: {content}")
                
                # 3. Parse Action
                action_data = self._parse_llm_action(content)
                if not action_data:
                    print("[WebAgent] Failed to parse action. Retrying or Stopping.")
                    # Retry logic omitted for brevity
                    break

                # 3.5 Check Guards (Policy Enforcement)
                guard_violation = self._check_guards(action_data, job.policy.guards)
                if guard_violation:
                    print(f"[WebAgent] Guard Violation: {guard_violation}")
                    self.guard_violations.append(guard_violation)
                    status = AgentRunStatus.BLOCKED
                    exit_reason = f"Guard violation: {guard_violation}"
                    break
                
                # 3.6 Check Takeover (Human Intervention Needed)
                if self._check_takeover(action_data):
                    print("[WebAgent] Takeover Triggered (Manual intervention required)")
                    self.takeover_triggered = True
                    status = AgentRunStatus.BLOCKED
                    exit_reason = "Takeover: Manual intervention required"
                    break

                # 4. Execute Action
                start_act = time.time()
                result = self._execute_action_with_result(device, action_data)
                success = result["status"] == "success"
                error_msg = result.get("message", "")
                latency = int((time.time() - start_act) * 1000)
                
                # 5. Record Step
                step_record = {
                    "i": i,
                    "ts": datetime.now().isoformat(),
                    "action": action_data,
                    "screen": f"evidence/screenshots/step_{i:03d}.png",
                    "status": "success" if success else "failed",
                    "error": error_msg,
                    "latency_ms": latency
                }
                steps.append(step_record)
                history.append(step_record)
                
                if self.on_step:
                    # Enrich callback data
                    self.on_step(step_record)
                
                # Check Finish
                if action_data["name"] == "Finish":
                    status = AgentRunStatus.FINISHED
                    exit_reason = action_data.get("args", {}).get("message", "Task Completed")
                    break
                
                # Wait a bit
                time.sleep(2)
                
                # Timeout
                if time.time() - start_time > job.run.timeout_sec:
                    status = AgentRunStatus.TIMEOUT
                    exit_reason = "Timeout"
                    break
            
        except Exception as e:
            status = AgentRunStatus.ERROR
            exit_reason = str(e)
            print(f"[WebAgent] Critical Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            device.disconnect()
            
        # Final artifacts
        steps_path = workspace / "steps.jsonl"
        with open(steps_path, "w") as f:
            for s in steps:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        
        final_path = screenshots_dir / "final.png"
        if steps:
            import shutil
            last_screen = workspace / steps[-1]["screen"]
            if last_screen.exists():
                shutil.copy(last_screen, final_path)
                
        return AgentRunResult(
            job_id=job.job_id,
            status=status,
            exit_reason=exit_reason,
            steps_jsonl_path=str(steps_path),
            screenshots_dir=str(screenshots_dir),
            final_screenshot_path=str(final_path),
            agent_verbose_log_path=str(workspace / "agent.log"),
            meta_path=str(workspace / "meta.json"),
            step_count=len(steps),
            guard_violations=self.guard_violations,
            takeover_triggered=self.takeover_triggered
        )

    def _build_prompt(self, task_text, dom_tree, step_index):
        # Very simple prompt construction
        dom_str = json.dumps(dom_tree)[:2000] # Truncate DOM if too large
        return f"""Task:
{task_text}

Current Step: {step_index}
Screen DOM (Truncated):
{dom_str}

Please output the next action in JSON format.
Actions:
- Tap(selector="...")
- Type(text="...", selector="...")
- Scroll(x=..., y=...)
- Navigate(url="...")
- Finish(message="...")

Example:
{{"name": "Type", "args": {{"selector": "#kw", "text": "keywords"}}}}
"""

    def _parse_llm_action(self, content):
        # Clean markdown code blocks
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        # Try finding JSON via brace counting
        try:
            start = content.find('{')
            if start == -1:
                return None
            
            # Simple brace counting
            count = 0
            json_str = ""
            found = False
            for char in content[start:]:
                json_str += char
                if char == '{':
                    count += 1
                elif char == '}':
                    count -= 1
                    if count == 0:
                        found = True
                        break
            
            if found:
                return json.loads(json_str)
        except:
            pass
            
        return None

    def _execute_action_with_result(self, device, action) -> dict:
        name = action.get("name")
        args = action.get("args", {})
        
        try:
            if name == "Navigate":
                device._driver.execute("navigate", {"url": args.get("url")})
                return {"status": "success"}
            elif name == "Tap":
                # If x,y provided
                if "x" in args and "y" in args:
                    device.tap(args["x"], args["y"])
                    return {"status": "success"}
                if "selector" in args:
                    device._driver.execute("click", {"selector": args["selector"]})
                    return {"status": "success"}
            elif name == "Type":
                # Pass selector if available
                if "selector" in args:
                    device._driver.execute("type", {"selector": args["selector"], "text": args.get("text")})
                else:
                    device.input_text(args.get("text"))
                return {"status": "success"}
            elif name == "Press":
                device._driver.execute("press", {"key": args.get("key", "Enter")})
                return {"status": "success"}
            elif name == "Scroll":
                device.swipe(0, 0, args.get("x", 0), args.get("y", 100))
                return {"status": "success"}
            elif name == "Finish":
                return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
        return {"status": "error", "message": "Unknown Action"}

    def _execute_action(self, device, action):
        return self._execute_action_with_result(device, action)["status"] == "success"

    def _check_guards(self, action: dict, guards: list[str]) -> str | None:
        """Check if action violates any guards (policy enforcement)."""
        action_str = json.dumps(action, ensure_ascii=False).lower()
        
        for guard in guards:
            keywords = GUARD_KEYWORDS.get(guard, [guard])
            for keyword in keywords:
                if keyword.lower() in action_str:
                    return guard
        
        return None
    
    def _check_takeover(self, action: dict) -> bool:
        """Check if action requires human intervention (takeover)."""
        action_str = json.dumps(action, ensure_ascii=False)
        
        for keyword in TAKEOVER_KEYWORDS:
            if keyword in action_str:
                return True
        
        return False

SYSTEM_PROMPT = """You are an intelligent Web Testing Agent.
Your goal is to complete the user's testing task on a browser.
You will receive a screenshot and a DOM tree.
Analyze the UI and determine the next action.

Rules:
1. Always return a SINGLE valid JSON object.
2. DO NOT use CSS Selectors (like #id, .class). They are unreliable.
3. Instead, use the **Visible Text** or **Placeholder** attributes to identify elements.
   - Example: If a button says "Submit", use label="Submit".
   - Example: If an input has placeholder "Search...", use label="Search...".
4. If you start a search type, remember to Press("Enter") afterwards.
5. If the page is loading, you can Wait.
6. If the task is done, call Finish.

Actions:
- Tap(label="...")  <-- Preferred: Click by text/placeholder
- Tap(x=..., y=...) <-- Fallback: Click by visual coordinates (0-1000 scale)
- Type(text="...", label="...") <-- Preferred: Type into input with this label/placeholder
- Press(key="Enter")
- Scroll(x=..., y=...)
- Navigate(url="...")
- Finish(message="...")

Example:
{{"name": "Type", "args": {{"label": "Search", "text": "keyword"}}}}
"""
