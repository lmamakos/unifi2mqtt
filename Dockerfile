FROM python:3.6-slim

WORKDIR /usr/src/app

COPY .   ./
RUN  pip install --no-cache-dir -r requirements.txt
CMD  exec python -m unifi2mqtt 
