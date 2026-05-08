FROM ghcr.io/home-assistant/base:3.21

ARG BUILD_VERSION="0.0.0"
ARG BUILD_ARCH="aarch64"

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.name="Umdu SPI U-Boot Flasher" \
    io.hass.description="Add-on для перезаписи U-Boot в SPI flash памяти" \
    io.hass.url="https://github.com/umduru/umdu-k1-uboot" \
    org.opencontainers.image.title="Umdu SPI U-Boot Flasher" \
    org.opencontainers.image.description="Add-on для перезаписи U-Boot в SPI flash памяти" \
    org.opencontainers.image.source="https://github.com/umduru/umdu-k1-uboot"

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
