import os
import asyncio
from runner.executor.runner import TaskRunner
from dotenv import load_dotenv

load_dotenv()

async def main():
    try:
        api_key = os.getenv("ZHIPU_API_KEY")
        print(f"API Key present: {bool(api_key)}")
        
        runner = TaskRunner(runs_dir="runs", mock=False, api_key=api_key, use_agent=True)
        
        bundle_path = "bundles/wechat_contacts_switch_bundle"
        device_id = "EP0110MZ0BB300817W"
        run_id = "debug_run_001"
        
        print(f"Starting run {run_id} with device {device_id}...")
        
        # Mock callback
        def on_step(data):
            print(f"Step: {data.get('action', {}).get('name')}")

        artifact = runner.run_with_agent(
            bundle_dir=bundle_path,
            device_id=device_id,
            on_step_callback=on_step,
            run_id=run_id
        )
        print("Run success!")
        
    except Exception as e:
        print("Run Failed!")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
