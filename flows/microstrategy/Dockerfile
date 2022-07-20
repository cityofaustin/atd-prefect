FROM python:3.8-slim
WORKDIR /app
COPY . /app
RUN chmod -R 755 /app/*
RUN cd /app && apt-get update && \
    pip install -r requirements.txt