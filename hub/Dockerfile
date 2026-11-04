FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3
COPY app/ /app/
# Bloc-notes database (hub-data volume). Owned by nobody (65534), the user the
# hardened compose runs the hub as, so the fresh named volume is writable.
RUN mkdir -p /data && chown 65534:65534 /data
ENV HANDOUT_DIR=/handouts
EXPOSE 5000
CMD ["python", "app.py"]
