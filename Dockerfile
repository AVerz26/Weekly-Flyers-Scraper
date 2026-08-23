FROM python:3.11-slim

WORKDIR /app

# Instala dependências de sistema se necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Expõe a porta do FastAPI
EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV SERVER_PORT=8000
ENV SERVER_HOST=0.0.0.0

CMD ["python", "app.py"]
