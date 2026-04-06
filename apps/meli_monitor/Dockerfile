FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY mercadolibre_monitor.py .

# Crear directorio para datos
RUN mkdir -p /data

# Ejecutar como usuario no-root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /data
USER appuser

ENTRYPOINT ["python", "mercadolibre_monitor.py"]
CMD ["check"]
