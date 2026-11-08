FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 gunicorn==22.0.0
COPY app/ /app/
ENV FLAG="TRIATHLON{placeholder}"
EXPOSE 5000
ENTRYPOINT ["/app/entrypoint.sh"]
