FROM ubuntu:bionic
LABEL maintainer="Peter Kolbus <peter.kolbus@gmail.com>"

RUN apt-get update \
    && apt-get -y install \
    default-jre-headless \
    git \
    ninja-build \
    python3-minimal \
    python3-pip \
    wget \
    && apt-get clean

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install -r /tmp/requirements.txt

CMD ["/bin/bash"]
