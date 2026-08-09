import asyncio
from jobhunter.frontend_data.sync_reader import load_review_queue

async def main():
    # This simulates running inside an existing event loop (like Streamlit)
    print("Inside asyncio.run, calling load_review_queue...")
    queue = load_review_queue()
    print(f"QUEUE: {queue}")
    return queue

if __name__ == "__main__":
    asyncio.run(main())