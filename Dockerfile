# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip uv
COPY pyproject.toml ./
RUN uv export --format requirements-txt --no-dev > requirements.txt
RUN pip install --no-cache-dir --target=/install -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY --from=builder /install /usr/local/lib/python3.11/site-packages
COPY src/ ./src/
COPY static/ ./static/
COPY alembic/ ./alembic/
COPY alembic.ini ./
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
