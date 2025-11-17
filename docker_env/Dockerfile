FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    bash \
    python3 \
    python3-pip \
    curl \
    iputils-ping \
    net-tools \
    nmap \
    procps \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN echo "This is a secret key file. Do not delete." > /secret_key.txt

CMD ["/bin/bash"]