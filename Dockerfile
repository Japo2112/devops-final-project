# ── Stage 1: Builder ──────────────────────────────────────────
# Instala gcc y compila las dependencias como wheels
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY app/backend/requirements.txt .

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt


# ── Stage 2: Final ────────────────────────────────────────────
# Imagen limpia sin compilador, solo copia los wheels ya compilados
FROM python:3.12-slim AS final

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --create-home appuser

WORKDIR /app

COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY app/backend/main.py .
COPY app/backend/templates/ ./templates/

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/live')"

# CRITICO: exec form con corchetes para que Gunicorn sea PID 1
# y reciba el SIGTERM directamente del sistema operativo
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--preload", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "main:app"]