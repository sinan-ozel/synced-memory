# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of synced-memory
- `Memory` class with Redis and DragonflyDB backends
- `PrefixedMemory` for scoped key namespacing
- Auto-synced `SyncedList` and `SyncedDict` collections
- Background flush queue for resilient offline operation
- Context manager support (`with Memory() as mem:`)
- Environment variable configuration (`REDIS_HOST`, `REDIS_PORT`, `REDIS_PREFIX`)
- Full CI/CD pipeline (tests, lint, docs validation)

[Unreleased]: https://github.com/sinan-ozel/synced-memory/compare/v0.1.0...HEAD
