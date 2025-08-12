FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y build-essential default-libmysqlclient-dev curl \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*
COPY utils.py worker_news.py worker_stocktwits.py fusion.py .
CMD ["python", "fusion.py"]
