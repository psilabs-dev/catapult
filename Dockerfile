FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y python3 python3-venv && \
    apt-get install -y gnupg apt-transport-https && \
    apt-get install -y erlang-base \
        erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
        erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
        erlang-runtime-tools erlang-snmp erlang-ssl \
        erlang-syntax-tools erlang-tftp erlang-tools erlang-xmerl && \
    apt-get install rabbitmq-server -y --fix-missing

WORKDIR /workdir

COPY requirements.txt       /workdir/requirements.txt
RUN python3 -m venv /opt/venv && pip3 install -r requirements.txt

COPY src                    /workdir/src
COPY pyproject.toml         /workdir/pyproject.toml

RUN pip3 install .