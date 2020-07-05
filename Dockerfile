FROM python:3

ADD bot.py /

RUN pip install boto3
RUN pip install requests

CMD ["python", "bot.py"]