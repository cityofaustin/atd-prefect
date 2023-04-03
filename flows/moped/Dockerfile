FROM ubuntu:20.04
ENV TZ="America/Chicago"
RUN apt-get update
RUN apt-get update && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
RUN apt-get upgrade -y
RUN apt-get install -y vim magic-wormhole aptitude python3-pip docker.io black libpq-dev zip jq curl inetutils-ping net-tools
COPY ./requirements.txt /root/requirements.txt
ENV PYTHONPATH "${PYTHONPATH}:/root/test_instance_deployment/atd-moped/moped-etl/prefect/"
RUN pip install -r /root/requirements.txt
RUN curl -L https://github.com/hasura/graphql-engine/raw/stable/cli/get.sh | bash
WORKDIR /root/
