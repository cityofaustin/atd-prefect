FROM python:slim

WORKDIR /prefect

COPY requirements.txt /prefect/requirements.txt

RUN apt-get update
RUN apt-get install gcc musl-dev libffi-dev -y
RUN pip install -r requirements.txt
