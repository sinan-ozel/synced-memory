# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-05-12

### Fixed

- `MemoryBase.sync()` now updates `_last_modified` before each write or
  enqueue, so nested collection edits (for example `mem.items.append(...)`)
  send a current timestamp and are not dropped by Redis-side conflict checks.
- `_load_from_redis` now stores list and dict values through `wrap_sync`, so
  after a failed reconnect `__getattr__` still returns `SyncedList` /
  `SyncedDict` and in-place nested updates propagate to the backend.

### Changed

- `SyncedList` and `SyncedDict` sync on additional in-place operations,
  including index and slice assign/delete, `clear`, `sort`, `reverse`,
  `+=` and `*=`, dict `del`, `clear`, `setdefault`, `popitem`, and `|=` (dict
  merge) on Python 3.9+; `append`, `extend`, and `insert` wrap nested
  list/dict values.

### Added

- Regression tests for the above, including load plus simulated unreachable
  Redis (`_connect` patched to fail).

## [0.1.2]

### Added

- Initial release of synced-memory
- `Memory` class with Redis and DragonflyDB backends
- `PrefixedMemory` for scoped key namespacing
- Auto-synced `SyncedList` and `SyncedDict` collections
- Background flush queue for resilient offline operation
- Context manager support (`with Memory() as mem:`)
- Environment variable configuration (`REDIS_HOST`, `REDIS_PORT`,
  `REDIS_PREFIX`)
- Full CI/CD pipeline (tests, lint, docs validation)

[Unreleased]: https://github.com/sinan-ozel/synced-memory/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/sinan-ozel/synced-memory/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/sinan-ozel/synced-memory/compare/v0.1.0...v0.1.2
