"""TimedInMemorySaver — InMemorySaver with background TTL-based thread eviction.

Not intended for direct use. Use ``create_checkpointer(ttl_seconds=...)`` instead.
"""

import logging
import threading
import time
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import ChannelVersions, Checkpoint, CheckpointMetadata
from langgraph.checkpoint.memory import InMemorySaver

logger = logging.getLogger(__name__)

_SWEEP_INTERVAL_SECONDS = 60


class TimedInMemorySaver(InMemorySaver):
    """InMemorySaver with background TTL-based thread eviction.

    Tracks last-active time per thread and evicts inactive threads via a
    daemon background sweep. The sweep is fully decoupled from the read/write
    path — ``put()`` only updates the activity timestamp.

    This approximates server-side TTL semantics for in-process storage:
    - ``put()`` records last-active timestamp (hot path stays clean)
    - A daemon sweep thread evicts inactive threads every 60 seconds
    - Eviction is best-effort — a thread may live up to
      ``ttl_seconds + 60`` seconds before deletion
    - State does not survive process restarts (inherent to InMemorySaver)

    Args:
        ttl_seconds: Inactivity threshold in seconds. Threads inactive for
                     longer than this are evicted. Default: 3600 (1 hour).

    Example::

        from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import (
            create_checkpointer,
        )

        checkpointer = create_checkpointer(ttl_seconds=3600)
    """

    def __init__(self, *, ttl_seconds: int = 3600, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.ttl_seconds = ttl_seconds
        self._last_active: dict[str, float] = {}
        self._lock = threading.Lock()
        self._sweeper = threading.Thread(
            target=self._sweep_loop,
            daemon=True,
            name="TimedInMemorySaver-sweeper",
        )
        self._sweeper.start()
        logger.debug(
            "TimedInMemorySaver started with ttl_seconds=%d, sweep_interval=%ds",
            ttl_seconds,
            _SWEEP_INTERVAL_SECONDS,
        )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Save checkpoint and refresh thread activity timestamp."""
        thread_id: str = config["configurable"]["thread_id"]
        with self._lock:
            self._last_active[thread_id] = time.monotonic()
        return super().put(config, checkpoint, metadata, new_versions)

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Async version of put — refreshes thread activity timestamp."""
        thread_id: str = config["configurable"]["thread_id"]
        with self._lock:
            self._last_active[thread_id] = time.monotonic()
        return await super().aput(config, checkpoint, metadata, new_versions)

    def _sweep_loop(self) -> None:
        while True:
            time.sleep(_SWEEP_INTERVAL_SECONDS)
            self._evict_expired()

    def _evict_expired(self) -> None:
        now = time.monotonic()
        with self._lock:
            expired = [
                tid
                for tid, ts in self._last_active.items()
                if now - ts > self.ttl_seconds
            ]
        for tid in expired:
            self.delete_thread(tid)
            with self._lock:
                self._last_active.pop(tid, None)
            logger.info(
                "TimedInMemorySaver: evicted inactive thread '%s' (inactive for >%ds)",
                tid,
                self.ttl_seconds,
            )
