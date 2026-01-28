build:
    docker build -t catering-api .

run:
    python manage.py runserver

docker:
    docker compose up -d database cache broker mailing

silpo-mock:
    python -m uvicorn test.providers.silpo:app --port 8001 --reload

kfc-mock:
    python -m uvicorn test.providers.kfc:app --port 8002 --reload

uklon-mock:
    python -m uvicorn test.providers.uklon:app --port 8001 --reload

worker-default:
    celery -A config worker -l INFO -Q default

worker-high:
    celery -A config worker -l INFO -Q high-priority