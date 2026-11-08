FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 gunicorn==22.0.0
COPY app/ /app/
ENV FLAG="TRIATHLON{placeholder}"
EXPOSE 5000
# gunicorn, 2 workers x 4 threads. --preload imports the app ONCE before forking, so the
# workers share module state set at import (e.g. a session key from os.urandom; without it
# each worker signs cookies differently and players get logged out at random).
# --worker-tmp-dir /dev/shm: the heartbeat file must not need a writable image.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", \
     "--preload", "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "app:app"]
