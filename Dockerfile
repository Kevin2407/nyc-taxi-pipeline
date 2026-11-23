# Imagen del pipeline: Python con dlt, dbt, Dagster y DuckDB.
# La usan los servicios del docker-compose que corren código nuestro.
FROM python:3.12-slim

# No escribir .pyc y mostrar los print en el log al instante (sin buffer).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git: dbt lo pide en su chequeo (dbt debug), aunque no usamos paquetes de terceros.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Primero solo requirements.txt: si el código cambia pero las dependencias no,
# Docker reutiliza esta capa y no reinstala todo.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Después el código. En desarrollo el compose monta la carpeta encima, así que
# los cambios se ven sin reconstruir la imagen.
COPY . .
