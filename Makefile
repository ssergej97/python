build:
    docker build -t catering-api .

docker:
    docker run --rm -p 8000:8000 catering-api