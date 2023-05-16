FROM python:3.9-alpine

WORKDIR /app

RUN apk add build-base linux-headers

COPY . .

RUN pip install -r requirements.txt

RUN pip install uwsgi

EXPOSE 5000

CMD [ "uwsgi", "--ini", "uwsgi.ini" ]