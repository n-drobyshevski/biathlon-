# Railway test deploy only (see deploy/railway/README.md). Build context: the
# repo root. Same app as challenges/01-web-staff/Dockerfile, plus the handout generator, so the
# evidence files are generated at start from the FLAG_* variables (Railway has
# no handouts/dist bind mount). Runs as nobody; only /out is writable.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends zip fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir flask==3.0.3 pillow==10.4.0 piexif==1.1.3
COPY handouts/generate.py /gen/generate.py
COPY handouts/assets /gen/assets
COPY challenges/01-web-staff/app/ /app/
COPY deploy/railway/with-handouts.sh /usr/local/bin/with-handouts
RUN chmod +x /usr/local/bin/with-handouts && mkdir -p /out && chown 65534:65534 /out
ENV HANDOUT_DIR=/out HOME=/tmp
USER 65534:65534
WORKDIR /app
EXPOSE 5000
CMD ["/usr/local/bin/with-handouts"]
