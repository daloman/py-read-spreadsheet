FROM python:3.11.2-slim-bullseye

WORKDIR /app

COPY py-read-spreadsheet.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

CMD [ "python", "py-read-spreadsheet.py" ]