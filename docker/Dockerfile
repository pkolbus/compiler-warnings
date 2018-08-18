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

# TODO: Replace with ubuntu-supplied package when LLVM 7 is released
RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key|apt-key add -
RUN echo "deb http://apt.llvm.org/bionic/ llvm-toolchain-bionic-7 main" >> /etc/apt/sources.list
RUN apt-get update \
    && apt-get -y install llvm-7 \
    && apt-get clean

RUN ln -s /usr/bin/llvm-tblgen-7 /usr/bin/llvm-tblgen

CMD ["/bin/bash"]
