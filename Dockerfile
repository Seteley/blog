FROM python:3.12-slim

# Instalar PostgreSQL dentro del mismo contenedor
RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/scripts/start.sh

EXPOSE 8000

CMD ["/app/scripts/start.sh"]
