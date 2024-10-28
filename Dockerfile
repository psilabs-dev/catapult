FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y python3 python3-venv

WORKDIR /workdir

COPY requirements.txt       /workdir/requirements.txt
RUN python3 -m venv /opt/venv && pip3 install -r requirements.txt

COPY src                    /workdir/src
COPY pyproject.toml         /workdir/pyproject.toml

RUN pip3 install --no-cache .