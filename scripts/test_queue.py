import asyncio
from uuid import uuid4

from app.workers.queue import job_queue


async def main() -> None:
    job_id = uuid4()

    print(f"Queue size before enqueue: {job_queue.size()}")

    await job_queue.enqueue(job_id)

    print(f"Queue size after enqueue: {job_queue.size()}")

    message = await job_queue.dequeue()

    print(f"Dequeued job ID: {message.job_id}")

    job_queue.task_done()

    print(f"Queue size after dequeue: {job_queue.size()}")


if __name__ == "__main__":
    asyncio.run(main())