FROM ubuntu:22.04
ENV TZ="America/Chicago"
RUN apt update
RUN apt-get update && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
RUN apt-get upgrade -y
RUN apt-get install -y vim magic-wormhole aptitude python3-pip docker.io rsync p7zip-full black poppler-utils tesseract-ocr
RUN pip install prefect
RUN pip install sysrsync GitPython boto3
RUN pip install pdf2image pytesseract
COPY ./prefect_bootstrap/ssh_config /root/.ssh/config
COPY ./prefect_bootstrap/id_rsa /root/.ssh/id_rsa
COPY ./prefect_bootstrap/id_rsa.pub /root/.ssh/id_rsa.pub
RUN chmod 600 /root/.ssh/id_rsa
RUN chmod 644 /root/.ssh/id_rsa.pub
WORKDIR /root/
