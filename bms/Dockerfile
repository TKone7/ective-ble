FROM python:3.11-bookworm

RUN apt-get update
RUN apt-get install -y bluez bluez-tools

WORKDIR /code

COPY requirements.txt /code/requirements.txt
RUN pip install -r requirements.txt

COPY . /code

CMD ["python", "ectiveBms.py"]
