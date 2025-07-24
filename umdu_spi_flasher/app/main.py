#!/usr/bin/env python3
import os
import subprocess
import logging
from flask import Flask, render_template_string, request, jsonify
import threading
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальные переменные для отслеживания состояния
flash_status = {"running": False, "success": None, "message": ""}

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
        button:disabled { background: #6c757d; cursor: not-allowed; }
        .status { padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center; }
        .status.running { background: #d1ecf1; color: #0c5460; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .hidden { display: none; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; display: inline-block; margin-right: 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
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

        <button id="flashBtn" onclick="startFlash()">Перезаписать U-Boot в SPI</button>
        
        <div id="status" class="status hidden">
            <div id="statusText"></div>
        </div>
    </div>

    <script>
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    const statusText = document.getElementById('statusText');
                    const flashBtn = document.getElementById('flashBtn');
                    
                    if (data.running) {
                        statusDiv.className = 'status running';
                        statusDiv.classList.remove('hidden');
                        statusText.innerHTML = '<div class="spinner"></div>' + data.message + ' НЕ ВЫКЛЮЧАЙТЕ УСТРОЙСТВО!';
                        flashBtn.disabled = true;
                    } else if (data.success === true) {
                        statusDiv.className = 'status success';
                        statusDiv.classList.remove('hidden');
                        statusText.innerHTML = '✅ Перезапись U-Boot завершена успешно!';
                        flashBtn.disabled = false;
                    } else if (data.success === false) {
                        statusDiv.className = 'status error';
                        statusDiv.classList.remove('hidden');
                        statusText.innerHTML = '❌ Ошибка: ' + data.message;
                        flashBtn.disabled = false;
                    } else {
                        statusDiv.classList.add('hidden');
                        flashBtn.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('Ошибка получения статуса:', error);
                });
        }

        function startFlash() {
            if (confirm('Вы уверены, что хотите перезаписать U-Boot? Процесс займет некоторое время и его нельзя прерывать!')) {
                fetch('/flash', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (!data.success) {
                            alert('Ошибка запуска: ' + data.message);
                        }
                    })
                    .catch(error => {
                        alert('Ошибка запуска: ' + error);
                    });
            }
        }

        // Обновляем статус каждые 2 секунды
        setInterval(updateStatus, 2000);
        updateStatus(); // Начальная проверка
    </script>
</body>
</html>
"""

def run_command(cmd, description):
    """Выполняет команду и возвращает результат"""
    logger.info(f"Выполняется: {description}")
    flash_status["message"] = description
    
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip() or "Неизвестная ошибка"
        raise Exception(f"{description}: {error_msg}")
    
    return result.stdout.strip()

def flash_uboot():
    """Функция для выполнения перезаписи U-Boot"""
    global flash_status
    
    try:
        flash_status = {"running": True, "success": None, "message": "Начало процесса..."}
        logger.info("Начало процесса перезаписи U-Boot")
        
        # Шаг 1: Скачиваем U-Boot файл
        run_command(
            'curl -L -o /tmp/u-boot-sunxi-with-spl.bin https://github.com/umduru/umdu-k1-uboot/raw/main/u-boot-sunxi-with-spl.bin',
            'Скачивание U-Boot файла...'
        )
        
        # Шаг 2: Очищаем SPI flash
        run_command(
            'flash_erase /dev/mtd0 0 0',
            'Очистка SPI flash памяти...'
        )
        
        # Шаг 3: Записываем U-Boot в SPI flash
        run_command(
            'flashcp -v /tmp/u-boot-sunxi-with-spl.bin /dev/mtd0',
            'Запись U-Boot в SPI flash...'
        )
        
        # Шаг 4: Синхронизируем
        run_command('sync', 'Синхронизация...')
        
        flash_status = {"running": False, "success": True, "message": "Перезапись завершена успешно"}
        logger.info("Перезапись U-Boot завершена успешно")
            
    except subprocess.TimeoutExpired:
        flash_status = {"running": False, "success": False, "message": "Превышено время ожидания"}
        logger.error("Превышено время ожидания выполнения команды")
    except Exception as e:
        flash_status = {"running": False, "success": False, "message": str(e)}
        logger.error(f"Ошибка перезаписи U-Boot: {e}")
    finally:
        # Удаляем временный файл
        try:
            os.remove('/tmp/u-boot-sunxi-with-spl.bin')
        except:
            pass

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    return jsonify(flash_status)

@app.route('/flash', methods=['POST'])
def flash():
    global flash_status
    
    if flash_status.get("running"):
        return jsonify({"success": False, "message": "Процесс уже выполняется"})
    
    # Запускаем процесс в отдельном потоке
    thread = threading.Thread(target=flash_uboot)
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True, "message": "Процесс запущен"})

if __name__ == '__main__':
    logger.info("Запуск UMDU SPI U-Boot Flasher")
    app.run(host='0.0.0.0', port=8099, debug=False) 