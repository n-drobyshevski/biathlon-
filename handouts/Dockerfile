# Toolbox image that generates all forensics / stego / SAP handout files.
# Kept tiny and arm64-native. Installs 'zip' for password-protected archives
# and DejaVu fonts for the poster text.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends zip fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pillow==10.4.0 piexif==1.1.3
WORKDIR /work
COPY handouts/generate.py /work/generate.py
# .env is passed via --env-file at run time; output is mounted at /out
CMD ["python", "/work/generate.py"]
