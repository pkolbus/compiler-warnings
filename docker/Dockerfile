FROM ubuntu:noble
LABEL maintainer="Peter Kolbus <peter.kolbus@gmail.com>"

RUN apt-get update \
    && apt-get -y install --no-install-recommends \
    default-jre-headless \
    git \
    llvm \
    ninja-build \
    python3-minimal \
    python3-virtualenv \
    shellcheck \
    wget \
    && apt-get clean

CMD ["/bin/bash"]
