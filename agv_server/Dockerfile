FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y curl dos2unix

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY requirements.txt .

RUN uv pip install -r requirements.txt --system

COPY . .

EXPOSE 8000

# Convert line endings from Windows (CRLF) to Unix (LF) and make executable
RUN dos2unix ./entrypoint.sh && chmod +x ./entrypoint.sh

CMD ["/bin/sh", "./entrypoint.sh"]

