"""DragonflyDB-specific Memory classes with DragonflyDB-fluent defaults."""

from synced_memory.common import (
    MemoryBase,
    PrefixedMemoryBase,
)
from synced_memory.common import (
    SyncedDict as SyncedDict,
)
from synced_memory.common import (
    SyncedList as SyncedList,
)
from synced_memory.common import (
    wrap_sync as wrap_sync,
)


class Memory(MemoryBase):
    """A synchronized key-value store backed by DragonflyDB.

    See MemoryBase for full documentation.
    """

    def __init__(
        self,
        dragonflydb_hostname: str = "dragonflydb",
        dragonflydb_port: int = 6379,
        db_prefix: str = "memory:",
        redis_prefix: str | None = None,
        dragonflydb_prefix: str | None = None,
    ):
        effective = redis_prefix or dragonflydb_prefix or db_prefix
        super().__init__(
            backend_hostname=dragonflydb_hostname,
            backend_port=dragonflydb_port,
            backend_prefix=effective,
        )


class PrefixedMemory(PrefixedMemoryBase):
    """Prefixed memory backed by DragonflyDB.

    Namespaces all keys by the given prefix scope.
    """

    def __init__(
        self,
        prefix: str,
        dragonflydb_hostname: str = "dragonflydb",
        dragonflydb_port: int = 6379,
        db_prefix: str = "memory:",
        redis_prefix: str | None = None,
        dragonflydb_prefix: str | None = None,
    ):
        effective = redis_prefix or dragonflydb_prefix or db_prefix
        super().__init__(
            prefix=prefix,
            backend_hostname=dragonflydb_hostname,
            backend_port=dragonflydb_port,
            backend_prefix=effective,
        )
