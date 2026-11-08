FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 gunicorn==22.0.0
COPY app.py /app/app.py
COPY templates/ /app/templates/
COPY static/ /app/static/
EXPOSE 8099
# ONE worker with several threads: the per-IP rate-limit counters live in memory
# and would be split (limit x workers) across processes. FLAG_FINALE and the
# optional answer overrides come from the environment (.env), never the image.
CMD ["gunicorn", "--bind", "0.0.0.0:8099", "--workers", "1", "--threads", "4", "app:app"]
