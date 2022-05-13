FROM ubuntu:22.04
ENV TZ="America/Chicago"
RUN apt update
RUN apt-get update && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
RUN apt upgrade -y
RUN apt install -y vim magic-wormhole aptitude python3-pip docker.io
RUN pip install prefect
RUN pip install sysrsync GitPython
WORKDIR /root/