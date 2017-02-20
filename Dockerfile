FROM python:2.7
MAINTAINER Olof Olsson "olof.olsson@snd.gu.se"
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["run.py"]