# syntax=docker/dockerfile:1
FROM python:3.14-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir pip==25.1.1 uv==0.10.12 \
    && uv export --format requirements-txt --no-dev > requirements.txt \
    && pip install --no-cache-dir --target=/install -r requirements.txt

FROM python:3.14-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY --from=builder /install /usr/local/lib/python3.14/site-packages
COPY src/ ./src/
COPY static/ ./static/
COPY alembic/ ./alembic/
COPY scripts/ ./scripts/
COPY alembic.ini ./
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app
# Оставляем root для entrypoint: chown на смонтированный ./logs
EXPOSE 8000
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "src.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
