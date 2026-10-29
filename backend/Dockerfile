FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements-base.lock /app/backend/requirements-base.lock
RUN pip install --no-cache-dir --require-hashes -r backend/requirements-base.lock
COPY backend /app/backend
COPY scripts /app/scripts
RUN useradd --create-home researcher && mkdir /app/data && chown researcher /app/data
USER researcher
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
