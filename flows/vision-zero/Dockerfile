FROM ubuntu:22.04
RUN apt update
RUN apt upgrade -y
RUN apt install -y vim magic-wormhole aptitude python3-pip docker.io
RUN pip install prefect
RUN pip install sysrsync GitPython
WORKDIR /root/