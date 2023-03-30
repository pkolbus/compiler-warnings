FROM debian:sid-slim
LABEL maintainer="Peter Kolbus <peter.kolbus@gmail.com>"

# Workaround for https://github.com/debuerreotype/debuerreotype/issues/10
# "error creating symbolic link '/usr/share/man/man1/rmid.1.gz.dpkg-tmp': No such file or directory"
RUN mkdir -p /usr/share/man/man1

RUN apt-get update \
    && apt-get -y install \
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
