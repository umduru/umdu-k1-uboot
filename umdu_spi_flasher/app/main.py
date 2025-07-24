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
        .info { background: #d1ecf1; color: #0c5460; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 5px; white-space: pre-wrap; text-align: left; }
    </style>
</head>
<body>
    <div class="container">
        <h1>UMDU SPI U-Boot Flasher</h1>
        
        <div class="warning">
            <strong>⚠️ ВНИМАНИЕ!</strong><br>
            Во время выполнения операции:<br>
            • НЕ ВЫКЛЮЧАЙТЕ устройство<br>
            • НЕ ОТКЛЮЧАЙТЕ питание<br>
            • НЕ ПЕРЕЗАГРУЖАЙТЕ систему<br>
            Прерывание процесса может привести к неработоспособности устройства!
        </div>

        <form method="post">
            <button type="submit" name="action" value="flash" onclick="return confirm('Вы уверены, что хотите перезаписать U-Boot? Процесс займет некоторое время и его нельзя прерывать!')">
                Перезаписать U-Boot в SPI
            </button>
        </form>
        
        {% if result %}
        <div class="result {{ result.type }}">
            {% if result.type == 'success' %}
                ✅ {{ result.message }}
            {% elif result.type == 'error' %}
                ❌ {{ result.message }}
            {% else %}
                ℹ️ {{ result.message }}
            {% endif %}
            
            {% if result.output %}
            <pre>{{ result.output }}</pre>
            {% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

def run_command(cmd, description):
    """Выполняет команду и возвращает результат"""
    logger.info(f"Выполняется: {description}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=120)
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Неизвестная ошибка"
            raise Exception(f"{description}: {error_msg}")
        
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise Exception(f"{description}: превышено время ожидания (120 сек)")

def flash_uboot():
    """Функция для выполнения перезаписи U-Boot"""
    output_log = []
    
    try:
        logger.info("Начало процесса перезаписи U-Boot")
        
        # Шаг 1: Скачиваем U-Boot файл
        output_log.append("1. Скачивание U-Boot файла...")
        result = run_command(
            'curl -L -o /tmp/u-boot-sunxi-with-spl.bin https://github.com/umduru/umdu-k1-uboot/raw/main/u-boot-sunxi-with-spl.bin',
            'Скачивание U-Boot файла'
        )
        output_log.append("   ✓ Файл скачан")
        
        # Шаг 2: Очищаем SPI flash
        output_log.append("2. Очистка SPI flash памяти...")
        result = run_command('flash_erase /dev/mtd0 0 0', 'Очистка SPI flash')
        output_log.append("   ✓ SPI flash очищен")
        
        # Шаг 3: Записываем U-Boot в SPI flash
        output_log.append("3. Запись U-Boot в SPI flash...")
        result = run_command('flashcp -v /tmp/u-boot-sunxi-with-spl.bin /dev/mtd0', 'Запись U-Boot')
        output_log.append("   ✓ U-Boot записан")
        
        # Шаг 4: Синхронизируем
        output_log.append("4. Синхронизация...")
        run_command('sync', 'Синхронизация')
        output_log.append("   ✓ Синхронизация завершена")
        
        output_log.append("\n✅ ПЕРЕЗАПИСЬ U-BOOT ЗАВЕРШЕНА УСПЕШНО!")
        logger.info("Перезапись U-Boot завершена успешно")
        
        return {
            "type": "success",
            "message": "Перезапись U-Boot завершена успешно!",
            "output": "\n".join(output_log)
        }
            
    except Exception as e:
        error_msg = str(e)
        output_log.append(f"\n❌ ОШИБКА: {error_msg}")
        logger.error(f"Ошибка перезаписи U-Boot: {e}")
        
        return {
            "type": "error", 
            "message": f"Ошибка: {error_msg}",
            "output": "\n".join(output_log)
        }
    finally:
        # Удаляем временный файл
        try:
            os.remove('/tmp/u-boot-sunxi-with-spl.bin')
        except:
            pass

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    
    if request.method == 'POST' and request.form.get('action') == 'flash':
        result = flash_uboot()
    
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == '__main__':
    logger.info("Запуск UMDU SPI U-Boot Flasher")
    app.run(host='0.0.0.0', port=8099, debug=False) 