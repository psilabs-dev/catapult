FROM python:3.11

WORKDIR /workdir

COPY requirements.txt       /workdir/requirements.txt
COPY catapult               /workdir/catapult
COPY pyproject.toml         /workdir/pyproject.toml

RUN pip3 install --no-cache .
CMD [ "uvicorn", "catapult.app:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info" ]
