FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y curl

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY requirements.txt .

RUN uv pip install -r requirements.txt --system

# Install dos2unix before copying files
RUN apt-get install -y dos2unix

COPY . .

EXPOSE 8000

# Use shell to run migrations and start server
CMD ["/bin/sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]

