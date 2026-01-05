
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.getcwd())

from runner.executor.web_agent_adapter import WebAgentAdapter
from runner.models.agent_job import AgentJob, ModelConfig, DeviceConfig, RunConfig

def test_web_agent():
    load_dotenv()
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        print("ZHIPU_API_KEY not found")
        return

    print("--- Starting Web Agent Verification ---")
    
    # Create Adapter
    adapter = WebAgentAdapter(api_key=api_key)
    
    # Create Job
    job = AgentJob(
        job_id="verify_web_001",
        task_text="Open https://www.bing.com and search for 'selenium'",
        model=ModelConfig(api_key=api_key),
        device=DeviceConfig(device_id="web", device_type="web"),
        run=RunConfig(max_steps=10),
        workspace_dir="runs/verify_web_001"
    )
    
    # Run
    result = adapter.run(job)
    
    print(f"Status: {result.status}")
    print(f"Steps: {result.step_count}")
    print(f"Exit Reason: {result.exit_reason}")
    print(f"Screenshots: {result.screenshots_dir}")

if __name__ == "__main__":
    test_web_agent()
