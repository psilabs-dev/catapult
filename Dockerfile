FROM python:3.12

WORKDIR /workdir

COPY requirements.txt       /workdir/requirements.txt
RUN python3 -m pip install -r requirements.txt

COPY src                    /workdir/src
COPY pyproject.toml         /workdir/pyproject.toml

RUN python3 -m pip install .