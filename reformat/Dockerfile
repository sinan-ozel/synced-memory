FROM python:3.12-slim

WORKDIR /workspace

# Copy pyproject.toml for dependency installation
COPY pyproject.toml /workspace/pyproject.toml
COPY src/ /workspace/src/

# Install dev dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy reformat script
COPY reformat/reformat.sh /workspace/reformat.sh
RUN chmod +x /workspace/reformat.sh

# Run the reformat script
CMD ["/workspace/reformat.sh"]
