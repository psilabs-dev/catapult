FROM python:3.11

WORKDIR /workdir

COPY requirements.txt /workdir/requirements.txt
COPY src                    /workdir/src
COPY pyproject.toml         /workdir/pyproject.toml

RUN pip3 install --no-cache .[satellite]
CMD [ "uvicorn", "catapult.satellite:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info" ]
