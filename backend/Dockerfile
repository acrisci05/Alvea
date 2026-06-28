# Dockerfile - Backend FastAPI Alvea
FROM python:3.12-slim

WORKDIR /app

# Dipendenze di sistema minime (bcrypt/cryptography hanno wheel pronte,
# build-essential serve solo come rete di sicurezza).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# host 0.0.0.0 = raggiungibile dall'esterno del container (app mobile, Swagger)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
