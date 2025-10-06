FROM python:3.11-slim
WORKDIR /app
COPY . /app
# Minimal deps used across tools in this folder: requests for HTTP; flask for positions_store service
RUN pip install --no-cache-dir requests flask
CMD ["python3", "token_daemon.py"]
