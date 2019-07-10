FROM python:3.6
MAINTAINER Spraakbanken "sb-info@svenska.gu.se"
COPY . /skbl
WORKDIR /skbl
RUN apt-get update
RUN apt-get install libicu-dev -y
RUN apt-get install python3-dev -y
RUN apt-get install libmemcached-dev -y
RUN pip install -r skbl/requirements.txt
ENTRYPOINT ["python3"]
CMD ["run.py"]
