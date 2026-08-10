import asyncio
from uuid import uuid4

import pytest

from app.workers.queue import JobQueue


@pytest.mark.asyncio
async def test_enqueue_and_dequeue():
    queue = JobQueue()
    job_id = uuid4()

    assert queue.size() == 0

    await queue.enqueue(job_id)

    assert queue.size() == 1

    message = await queue.dequeue()

    assert message.job_id == job_id
    assert queue.size() == 0

    queue.task_done()


@pytest.mark.asyncio
async def test_multiple_jobs_preserve_order():
    queue = JobQueue()

    job_ids = [uuid4() for _ in range(3)]

    for job_id in job_ids:
        await queue.enqueue(job_id)

    assert queue.size() == 3

    messages = []

    for _ in range(3):
        message = await queue.dequeue()
        messages.append(message.job_id)
        queue.task_done()

    assert messages == job_ids
    assert queue.size() == 0


@pytest.mark.asyncio
async def test_dequeue_waits_for_job():
    queue = JobQueue()
    job_id = uuid4()

    async def add_job():
        await asyncio.sleep(0.05)
        await queue.enqueue(job_id)

    producer = asyncio.create_task(add_job())

    message = await queue.dequeue()

    assert message.job_id == job_id

    queue.task_done()

    await producer