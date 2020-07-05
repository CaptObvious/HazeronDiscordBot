FROM python:3

ADD bot.py /

RUN pip3 install boto3
RUN pip3 install requests

CMD ["python", "bot.py"]