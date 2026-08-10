import asyncio
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class JobMessage:
    """
    Message placed on the processing queue.

    Only the processing ID is passed through the queue.
    The worker retrieves the complete job from PostgreSQL.
    """

    job_id: UUID


class JobQueue:
    """
    Application-level queue abstraction.

    The underlying implementation currently uses
    asyncio.Queue so it can later be replaced by
    Redis, RabbitMQ, SQS, etc. without changing
    the API layer.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[JobMessage] = asyncio.Queue()

    async def enqueue(self, job_id: UUID) -> None:
        """Add a processing job to the queue."""
        await self._queue.put(JobMessage(job_id=job_id))

    async def dequeue(self) -> JobMessage:
        """Wait until a processing job is available."""
        return await self._queue.get()

    def task_done(self) -> None:
        """Mark the current queue item as processed."""
        self._queue.task_done()

    def size(self) -> int:
        """Return the number of jobs currently waiting."""
        return self._queue.qsize()


job_queue = JobQueue()