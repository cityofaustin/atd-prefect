FROM ubuntu:22.04
ENV TZ="America/Chicago"
RUN apt-get update
RUN apt-get update && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
RUN apt-get upgrade -y
RUN apt-get install -y vim magic-wormhole aptitude python3-pip docker.io rsync p7zip-full black poppler-utils tesseract-ocr wget postgresql-client pgloader postgresql-common libpq-dev
COPY ./requirements.txt /root/requirements.txt
RUN pip install -r /root/requirements.txt
COPY ./prefect_bootstrap/ssh_config /root/.ssh/config
COPY ./prefect_bootstrap/id_rsa /root/.ssh/id_rsa
COPY ./prefect_bootstrap/id_rsa.pub /root/.ssh/id_rsa.pub
COPY ./prefect_bootstrap/prefect.config.toml /root/.prefect/config.toml
RUN chmod 600 /root/.ssh/id_rsa
RUN chmod 644 /root/.ssh/id_rsa.pub
WORKDIR /root/

# The following two lines inflate build times and image size, but they provide man pages in the image.
# If, in the future, we find ourselves motivated to crush down this image size, such as if it were to be
# useful to the public at large and accumulating lots of downloads, we can disable these lines.
# RUN apt-get install -y man-db
# RUN yes | unminimize
