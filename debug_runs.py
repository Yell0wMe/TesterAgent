import asyncio
from server.services.task_manager import manager

async def main():
    try:
        print("Listing runs...")
        runs = manager.list_runs()
        print(f"Runs: {runs}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
