# Help from: https://github.com/cohere-ai/cohere-toolkit/blob/main/src/backend/Dockerfile

FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
# PYTHONPATH includes both src/ (for backend.*) and /workspace/ (for crm.*)
ENV PYTHONPATH=/workspace/src/:/workspace/
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

ENV VIRTUAL_ENV=/workspace/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /workspace

# Copy dependency files to avoid cache invalidations
COPY pyproject.toml poetry.lock ./

COPY src/backend/ src/backend/

# Copy the crm/ client package (used by backend/intel/router.py)
COPY crm/ crm/

RUN pip install --no-cache-dir poetry && poetry install

EXPOSE 8000

# Run alembic migrations if DB is available, then start uvicorn
# alembic failure is non-fatal (DB may not be ready yet on first boot)
CMD ["sh", "-c", "cd /workspace/src/backend && (alembic upgrade head || echo 'alembic skipped - DB not ready') && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
