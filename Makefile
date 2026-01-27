build:
    docker build -t catering-api .

docker:
    docker run --rm -p 8000:8000 catering-api

worker-default:
    celery -A config worker -l INFO -Q default

worker-high:
    celery -A config worker -l INFO -Q high-priority