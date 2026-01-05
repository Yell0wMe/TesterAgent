import asyncio
import os
import sys
from pathlib import Path

# Add src to python path
sys.path.append(os.path.abspath("src"))

from server.services.task_manager import task_manager

async def test_create_direct():
    try:
        print("Testing create_direct_run...")
        run_id = await task_manager.create_direct_run(
            device_id="mock",
            instruction="Open settings",
            config={}
        )
        print(f"Success! Run ID: {run_id}")
    except Exception as e:
        print(f"Failed! Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_create_direct())
