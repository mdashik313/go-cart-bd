FROM python:3.14.4
WORKDIR /app
ENV PYTHONUNBUFFERED=1

ADD req.txt /app/
RUN pip install -r /app/req.txt 

COPY . /app
