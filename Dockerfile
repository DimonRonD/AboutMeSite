FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GUNICORN_BIND=0.0.0.0:5000
ENV GUNICORN_WORKERS=2
ENV GUNICORN_THREADS=4
ENV GUNICORN_TIMEOUT=120
ENV GUNICORN_GRACEFUL_TIMEOUT=30
ENV GUNICORN_KEEPALIVE=5

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/database /app/logs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --bind ${GUNICORN_BIND} --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT} --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT} --keep-alive ${GUNICORN_KEEPALIVE} \"app:create_app()\""]
