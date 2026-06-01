FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN mkdir -p /app/data && chmod 0777 /app/data

RUN apt-get update \
    && apt-get install -y --no-install-recommends ttyd ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8080

CMD ["sh", "-c", "ttyd -p ${PORT:-8080} -c ${TTYD_CREDENTIALS:-admin:admin} --watch=false python -m bagels --at /data"]
