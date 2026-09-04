# Etapa 1: imagem base
FROM python:3.11-slim

WORKDIR /app

# Instala dependências Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

EXPOSE 8003

# Executa com Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8003", "app:app"]