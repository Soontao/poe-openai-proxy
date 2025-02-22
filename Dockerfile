FROM python:3.9-alpine

WORKDIR /app

RUN apk add build-base linux-headers

COPY . .

RUN pip install -r requirements.txt

EXPOSE 5000

CMD [ "python", "api.py" ]