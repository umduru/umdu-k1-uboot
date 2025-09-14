ARG BUILD_FROM
FROM $BUILD_FROM

# Установка необходимых пакетов для работы с SPI flash
RUN apk add --no-cache \
    bash \
    curl \
    wget \
    mtd-utils \
    python3 \
    py3-pip \
    py3-flask

# Создание рабочей директории
WORKDIR /app

# Копирование приложения
COPY app /app/

# Отключаем S6 overlay и используем простой bash
ENTRYPOINT []
CMD [ "python3", "-u", "main.py" ] 