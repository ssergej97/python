FROM python:3.13-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update -y \
    && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip setuptools pipenv

COPY Pipfile Pipfile.lock ./


COPY . .

from base as dev

RUN pipenv install sync --dev --system

from base as prod

RUN pipenv install --deploy --system

EXPOSE 8000/tcp
ENTRYPOINT ["python"]
CMD ["-m", "gunicorn", "config.wsgi:application"]

from base as silpo

RUN pipenv install sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT ["python"]
CMD ["-m", "uvicorn", "test.providers.silpo:app", "--host", "0.0.0.0"]

from base as kfc

RUN pipenv install sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT ["python"]
CMD ["-m", "uvicorn", "test.providers.kfc:app", "--host", "0.0.0.0"]

from base as uklon

RUN pipenv install sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT ["python"]
CMD ["-m", "uvicorn", "test.providers.uklon:app", "--host", "0.0.0.0"]
