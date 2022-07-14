FROM ubuntu:20.04
ENV TZ="America/Chicago"
RUN apt update
RUN apt-get update && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
RUN apt-get upgrade -y
RUN apt-get install -y vim magic-wormhole aptitude python3-pip docker.io black libpq-dev python3.8-venv
RUN pip install prefect
RUN pip install boto3
# the following line needs to be removed
RUN pip install python-dotenv
RUN pip install psycopg2-binary
RUN pip install zappa
WORKDIR /root/
