FROM python:3.9-alpine

WORKDIR /app

RUN apk add build-base

COPY . .

RUN pip install -r requirements.txt

EXPOSE 5000

CMD [ "uwsgi", "--ini", "uwsgi.ini" ]