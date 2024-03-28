FROM python:3-slim

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update --fix-missing && \
    apt-get install --no-install-recommends -y sqlite3 && \
    apt-get clean

RUN useradd -M -s /sbin/nologin www

WORKDIR /var/www

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY templates/ templates/.
COPY app.py .
COPY schema.sql .

RUN cat schema.sql | sqlite3 /tmp/shop.db
RUN chmod ugo+w /tmp/shop.db

USER www

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
