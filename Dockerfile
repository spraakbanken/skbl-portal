FROM python:3.10
LABEL maintainer="sb-info@svenska.gu.se"
RUN apt-get update
RUN apt-get install libicu-dev -y
RUN apt-get install python3-dev -y
RUN apt-get install libmemcached-dev -y
COPY skbl/requirements.txt /skbl/requirements.txt
RUN pip install -r skbl/requirements.txt
COPY . /skbl/
WORKDIR /skbl

ENTRYPOINT ["python3"]
CMD ["run.py"]
