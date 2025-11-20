FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update --fix-missing

RUN apt-get install -y --no-install-recommends \
    bash python3 python3-pip python3-requests

RUN apt-get install -y --no-install-recommends \
    curl wget iputils-ping net-tools

RUN apt-get install -y --no-install-recommends \
    nmap netcat-openbsd procps lsof

RUN apt-get install -y --no-install-recommends \
    vim nano tree file

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /sandbox /data
RUN chmod 777 /sandbox /data


RUN echo "This is a secret key file. Do not delete." > /secret_key.txt

CMD ["/usr/bin/tail", "-f", "/dev/null"]