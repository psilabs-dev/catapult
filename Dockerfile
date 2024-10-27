FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3 python3-venv

WORKDIR /workdir

COPY requirements.txt       /workdir/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip3 install -r requirements.txt

COPY src                    /workdir/src
COPY pyproject.toml         /workdir/pyproject.toml

ENV PATH="/opt/venv/bin:$PATH"
RUN pip3 install .