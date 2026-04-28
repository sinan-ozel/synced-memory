# Development Setup

## Prerequisites

- **Docker**: Required for all development workflows
- **Git**: For version control
- **VS Code**: Optional but recommended

## Setup Options

### Option 1: VS Code Dev Containers (Recommended)

1. Open the project in VS Code
2. Install the "Dev Containers" extension
3. Press `Cmd/Ctrl + Shift + P` → "Dev Containers: Reopen in Container"

The devcontainer includes Python 3.11, Redis, and all dependencies pre-installed.

### Option 2: Docker Compose

**Run tests:**
```bash
docker compose -f tests/docker-compose.yaml up --build --abort-on-container-exit --exit-code-from test
```

**Reformat code:**
```bash
docker compose -f reformat/docker-compose.yaml up --build --abort-on-container-exit
```

**Validate docs:**
```bash
docker compose -f docs-validate/docker-compose.yaml up --build --abort-on-container-exit
```

### Option 3: Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -e .
pip install -e .[test]
pip install -e .[dev]
pip install -e .[docs]
```

Start a Redis or DragonflyDB backend:

```bash
docker run -d -p 6379:6379 redis:7
```

## Verifying Your Setup

```python
from synced_memory.redis import Memory

mem = Memory()
mem.test = "Hello, synced-memory!"
print(mem.test)  # Hello, synced-memory!
```

Run the test suite:

```bash
pytest tests/ -v
```

## Project Structure

```
synced-memory/
├── .devcontainer/          # Dev container configuration
├── .github/workflows/ci.yaml
├── .vscode/tasks.json
├── docs/                   # Documentation source
├── docs-validate/          # Docs validation Docker setup
├── lint/                   # Linting Docker setup
├── reformat/               # Code formatting Docker setup
├── scripts/                # Utility scripts
├── src/
│   └── synced_memory/
│       ├── __init__.py
│       ├── redis/
│       │   └── __init__.py   # Redis backend
│       └── dragonflydb/
│           └── __init__.py   # DragonflyDB backend
├── tests/
│   ├── test_redis.py         # Redis test suite
│   └── docker-compose.yaml   # Test environment (Redis + DragonflyDB)
├── mkdocs.yml
└── pyproject.toml
```

## Common Issues

**Redis Connection Error:**
- Ensure Redis is running: `redis-cli ping` should return `PONG`
- Check `REDIS_HOST` environment variable

**Import Error (`ModuleNotFoundError: No module named 'synced_memory'`):**
```bash
pip install -e .
```

**Port already in use (6379):**
```bash
lsof -i :6379 && kill -9 <PID>
```
