FROM python:3.10
ENV PYTHONUNBUFFERED 1

# Устанавливаем рабочую директорию
WORKDIR /code/image_shop  
COPY requirements.txt .
RUN pip install -r requirements.txt

# Затем копируем ВСЁ содержимое проекта
COPY . .

EXPOSE 8000