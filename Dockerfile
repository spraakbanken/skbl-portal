FROM python:2.7
MAINTAINER Olof Olsson "olof.olsson@snd.gu.se"
COPY . /app
WORKDIR /app
RUN apt-get update
RUN apt-get install libicu-dev -y
RUN apt-get install python-dev -y
RUN pip install -r app/requirements.txt
ENTRYPOINT ["python"]
CMD ["run.py"]
