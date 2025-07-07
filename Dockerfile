# Usar Python 3.12 como imagen base
FROM python:3.12-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar los archivos de requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Crear directorios necesarios
RUN mkdir -p /app/data /app/temp /app/logs /app/ffmpeg_bin

# Copiar el código de la aplicación
COPY . .

# Asegurar que ffmpeg está disponible
RUN chmod +x /app/ffmpeg_bin/ffmpeg || true

# Crear usuario no-root para ejecutar la aplicación
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

# Exponer puerto para healthcheck
EXPOSE 8000

# Configurar variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Comando por defecto para ejecutar el bot
CMD ["python", "bot.py"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1
