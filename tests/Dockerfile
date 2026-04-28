FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --upgrade pip
RUN pip install .
RUN pip install .[test]

CMD ["pytest", "tests/"]
