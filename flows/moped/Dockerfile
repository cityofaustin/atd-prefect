FROM ubuntu:22.04
ENV TZ="America/Chicago"
RUN apt update
RUN apt-get update && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
RUN apt-get upgrade -y
RUN apt-get install -y vim magic-wormhole aptitude python3-pip docker.io black
RUN pip install prefect
RUN pip install boto3
RUN pip install python-dotenv
RUN pip install psycopg2-binary
RUN pip install zappa
WORKDIR /root/
