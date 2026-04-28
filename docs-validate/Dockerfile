FROM python:3.11-slim

WORKDIR /workspace

# Copy only pyproject.toml to install dependencies
COPY pyproject.toml /tmp/pyproject.toml
COPY src/synced_memory/ /tmp/src/synced_memory/

RUN pip install --upgrade pip && \
    cd /tmp && \
    pip install . && \
    pip install .[docs] && \
    rm -rf /tmp/*

# Files will be mounted at /workspace
CMD ["mkdocs", "build", "--strict"]
