"""Redis-specific Memory classes with Redis-fluent defaults."""

from synced_memory.common import (
    MemoryBase,
    PrefixedMemoryBase,
    SyncedDict,
    SyncedList,
    wrap_sync,
)


class Memory(MemoryBase):
    """A synchronized key-value store backed by Redis.

    See MemoryBase for full documentation.
    """

    def __init__(
        self,
        redis_hostname: str = "redis",
        redis_port: int = 6379,
        db_prefix: str = "memory:",
        redis_prefix: str | None = None,
        dragonflydb_prefix: str | None = None,
    ):
        effective = redis_prefix or dragonflydb_prefix or db_prefix
        super().__init__(
            backend_hostname=redis_hostname,
            backend_port=redis_port,
            backend_prefix=effective,
        )


class PrefixedMemory(PrefixedMemoryBase):
    """Prefixed memory backed by Redis.

    Namespaces all keys by the given prefix scope.
    """

    def __init__(
        self,
        prefix: str,
        redis_hostname: str = "redis",
        redis_port: int = 6379,
        db_prefix: str = "memory:",
        redis_prefix: str | None = None,
        dragonflydb_prefix: str | None = None,
    ):
        effective = redis_prefix or dragonflydb_prefix or db_prefix
        super().__init__(
            prefix=prefix,
            backend_hostname=redis_hostname,
            backend_port=redis_port,
            backend_prefix=effective,
        )
