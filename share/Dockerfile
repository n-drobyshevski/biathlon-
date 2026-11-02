FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3
COPY app/ /app/
ENV HANDOUT_DIR="/handouts" \
    SHARE_USER="equipe-it" \
    SHARE_PASSWORD="transition2026"
EXPOSE 5000
CMD ["python", "app.py"]
