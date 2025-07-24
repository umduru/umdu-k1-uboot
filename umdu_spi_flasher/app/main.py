#!/usr/bin/env python3
import os
import subprocess
import logging
from flask import Flask, render_template_string, request

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# HTML шаблон интерфейса
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UMDU SPI U-Boot Flasher</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .warning strong { color: #b7791f; }
        button { background: #007bff; color: white; border: none; padding: 15px 30px; font-size: 16px; border-radius: 5px; cursor: pointer; width: 100%; margin: 10px 0; }
        button:hover { background: #0056b3; }
        .result { padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>UMDU SPI U-Boot Flasher</h1>
        
        <div class="warning">
            <strong>⚠️ ВНИМАНИЕ!</strong><br>
            Во время выполнения операции:<br>
            • НЕ ВЫКЛЮЧАЙТЕ устройство<br>
            • НЕ ПЕРЕЗАГРУЖАЙТЕ систему
        </div>

        <form method="post">
            <button type="submit" onclick="return confirm('Вы уверены, что хотите перезаписать U-Boot?')">
                Перезаписать U-Boot в SPI
            </button>
        </form>
        
        {% if result %}
        <div class="result {{ result.type }}">
            {% if result.type == 'success' %}
                ✅ {{ result.message }}
            {% else %}
                ❌ {{ result.message }}
            {% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

def flash_uboot():
    """Функция для выполнения перезаписи U-Boot"""
    try:
        logger.info("Начало процесса перезаписи U-Boot")
        
        # Скачиваем U-Boot файл
        logger.info("Скачивание U-Boot файла...")
        subprocess.run('curl -L -o /tmp/u-boot-sunxi-with-spl.bin https://github.com/umduru/umdu-k1-uboot/raw/main/u-boot-sunxi-with-spl.bin', shell=True, check=True)
        
        # Очищаем SPI flash
        logger.info("Очистка SPI flash...")
        subprocess.run('flash_erase /dev/mtd0 0 0', shell=True, check=True)
        
        # Записываем U-Boot
        logger.info("Запись U-Boot...")
        subprocess.run('flashcp -v /tmp/u-boot-sunxi-with-spl.bin /dev/mtd0', shell=True, check=True)
        
        # Синхронизируем
        subprocess.run('sync', shell=True, check=True)
        
        logger.info("✅ Перезапись завершена успешно")
        return {"type": "success", "message": "Перезапись U-Boot завершена успешно!"}
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return {"type": "error", "message": f"Ошибка: {e}"}
    finally:
        try:
            os.remove('/tmp/u-boot-sunxi-with-spl.bin')
        except:
            pass

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        result = flash_uboot()
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == '__main__':
    logger.info("Запуск UMDU SPI U-Boot Flasher")
    app.run(host='0.0.0.0', port=8099, debug=False) 