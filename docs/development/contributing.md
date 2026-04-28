# Contributing

Thank you for your interest in contributing to synced-memory!

## Getting Started

### Prerequisites

- Docker (required)
- Git
- VS Code (optional, recommended for devcontainer support)

### Fork and Clone

```bash
git clone https://github.com/sinan-ozel/synced-memory.git
cd synced-memory
```

## Development Environment

### Option 1: VS Code Dev Containers (Recommended)

1. Open the project in VS Code
2. Install the "Dev Containers" extension
3. Press `Cmd/Ctrl + Shift + P` → "Dev Containers: Reopen in Container"

### Option 2: Docker Compose

```bash
docker compose -f tests/docker-compose.yaml up --build --abort-on-container-exit --exit-code-from test
```

### Option 3: Local Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e .
pip install -e .[test]
pip install -e .[dev]
pip install -e .[docs]
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Use prefixes: `feature/`, `bugfix/`, `docs/`, `refactor/`

### 2. Run Tests

```bash
docker compose -f tests/docker-compose.yaml up --build --abort-on-container-exit --exit-code-from test
```

### 3. Format and Lint

```bash
docker compose -f reformat/docker-compose.yaml up --build --abort-on-container-exit
docker compose -f lint/docker-compose.yaml up --build --abort-on-container-exit --exit-code-from linter
```

Or manually:

```bash
black src/
isort src/
ruff check src/
```

### 4. Commit and Push

Use conventional commit prefixes: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`

### 5. Open a PR

Create a Pull Request on GitHub with a clear title and description of the change.

## Code Style

- Follow PEP 8, use type hints, write Google-style docstrings
- Max line length: 80 characters, enforced by `black`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
