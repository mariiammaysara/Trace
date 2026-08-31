FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

# Entrypoint will be defined once the API/service layer is implemented.
CMD ["python", "--version"]
