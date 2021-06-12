FROM python:3.7 as builder

COPY ./requirements.txt .

RUN pip install --upgrade pip && \
    pip install --user -r requirements.txt

FROM python:3.7-slim

RUN apt-get -y update && \
    apt-get install -qy apt-utils libpq5 && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY ./auxy ./auxy
COPY ./modular_aiogram_handlers ./modular_aiogram_handlers
COPY ./alembic.ini ./alembic.ini
COPY ./docker-entrypoint.sh ./docker-entrypoint.sh

ENV PATH=/root/.local:$PATH

CMD ["./docker-entrypoint.sh"]
