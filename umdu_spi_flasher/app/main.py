#!/usr/bin/env python3
import os
import threading
import subprocess
import logging
from flask import Flask, render_template_string, request, jsonify

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальная блокировка, чтобы не запускать прошивку параллельно
flash_lock = threading.Lock()

# HTML шаблон интерфейса
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Umdu SPI U-Boot Flasher</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .warning strong { color: #b7791f; }
        button { background: #007bff; color: white; border: none; padding: 15px 30px; font-size: 16px; border-radius: 5px; cursor: pointer; width: 100%; margin: 10px 0; }
        button:hover { background: #0056b3; }
        button:disabled { background: #ffc107; color: #856404; cursor: not-allowed; }
        .result { padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        /* Журнал: ограничиваем и предотвращаем выход за границы */
        details { margin: 10px 0; }
        details > summary { cursor: pointer; }
        pre { 
            max-width: 100%;
            max-height: 360px;
            overflow: auto;           /* скролл если не помещается */
            white-space: pre;         /* сохраняем форматирование без переноса */
            background: #f6f8fa; 
            color: #24292e;
            padding: 12px; 
            border-radius: 6px; 
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 12px;
            line-height: 1.4;
            box-sizing: border-box;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Umdu SPI U-Boot Flasher</h1>
        
        <div class="warning">
            <strong>⚠️ ВНИМАНИЕ!</strong><br>
            Во время выполнения операции:<br>
            • НЕ ВЫКЛЮЧАЙТЕ устройство<br>
            • НЕ ПЕРЕЗАГРУЖАЙТЕ систему
        </div>

        <form method="post" onsubmit="document.querySelector('button').disabled=true; document.querySelector('button').textContent='Ожидайте... НЕ ВЫКЛЮЧАЙТЕ УСТРОЙСТВО!';">
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
        {% if result.logs %}
        <details>
            <summary>Показать журнал выполнения</summary>
            <pre>{{ result.logs }}</pre>
        </details>
        {% endif %}
        {% endif %}
    </div>
    <script>
    (function(){
        const btn = document.querySelector('button[type="submit"]') || document.querySelector('button');
        if (!btn) return;
        const originalText = btn.textContent;
        async function poll(){
            try {
                const res = await fetch('status', { cache: 'no-store' });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();
                if (data && data.running) {
                    btn.disabled = true;
                    btn.textContent = 'Идёт прошивка... НЕ ВЫКЛЮЧАЙТЕ УСТРОЙСТВО!';
                } else {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            } catch (e) {
                // В случае ошибки статуса не меняем текущий вид
            }
        }
        poll();
        setInterval(poll, 3000);
    })();
    </script>
</body>
</html>
"""

def run_cmd(cmd, log_buffer, step=None, timeout=None):
    """Запуск команды с захватом stdout/stderr и подробным логированием."""
    if step:
        logger.info(step)
        log_buffer.append(f"==> {step}")
    logger.info(f"Выполнение: {cmd}")
    log_buffer.append(f"$ {cmd}")
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.stdout:
            logger.info(proc.stdout.strip())
            log_buffer.append(proc.stdout.rstrip())
        if proc.stderr:
            # Многие утилиты пишут прогресс в stderr
            logger.info(proc.stderr.strip())
            log_buffer.append(proc.stderr.rstrip())
        return proc
    except subprocess.CalledProcessError as e:
        logger.error(
            "Команда завершилась с ошибкой (код %s): %s",
            e.returncode,
            cmd,
        )
        if e.stdout:
            logger.error("stdout:\n%s", e.stdout.strip())
            log_buffer.append(e.stdout.rstrip())
        if e.stderr:
            logger.error("stderr:\n%s", e.stderr.strip())
            log_buffer.append(e.stderr.rstrip())
        raise
    except subprocess.TimeoutExpired as e:
        logger.error("Таймаут выполнения команды: %s (timeout=%ss)", cmd, e.timeout)
        log_buffer.append(f"[ОШИБКА] Таймаут выполнения команды спустя {e.timeout}s: {cmd}")
        raise

def flash_uboot():
    """Функция для выполнения перезаписи U-Boot"""
    try:
        logger.info("Начало процесса перезаписи U-Boot")
        logs = []
        acquired = flash_lock.acquire(blocking=False)
        if not acquired:
            logger.warning("Попытка запустить прошивку, пока предыдущая операция ещё выполняется")
            return {
                "type": "error",
                "message": "Операция уже выполняется. Подождите завершения текущей прошивки.",
            }
        
        # Скачиваем U-Boot файл
        run_cmd(
            'curl -L --fail --retry 3 --retry-delay 2 --connect-timeout 10 --max-time 120 -o /tmp/u-boot-sunxi-with-spl.bin https://github.com/umduru/umdu-k1-uboot/raw/main/u-boot-sunxi-with-spl.bin',
            logs,
            step="Скачивание U-Boot файла",
            timeout=180,
        )
        
        # Очищаем SPI flash
        run_cmd('flash_erase /dev/mtd0 0 0', logs, step="Очистка SPI flash", timeout=600)
        
        # Записываем U-Boot
        run_cmd(
            'flashcp -v /tmp/u-boot-sunxi-with-spl.bin /dev/mtd0',
            logs,
            step="Запись U-Boot в SPI",
            timeout=600,
        )
        
        # Синхронизируем
        run_cmd('sync', logs, step="Синхронизация изменений", timeout=60)
        
        logger.info("✅ Перезапись завершена успешно")
        return {
            "type": "success",
            "message": "Перезапись U-Boot завершена успешно!",
            "logs": "\n".join(logs),
        }
        
    except subprocess.CalledProcessError as e:
        # Ошибка уже залогирована в run_cmd; возвращаем содержимое лога пользователю
        logger.exception("Ошибка при выполнении шага прошивки")
        return {
            "type": "error",
            "message": f"Ошибка при выполнении команды (код {e.returncode}). Подробности в журнале ниже.",
            "logs": "\n".join(logs),
        }
    except subprocess.TimeoutExpired as e:
        logger.exception("Таймаут шага прошивки")
        return {
            "type": "error",
            "message": f"Превышено время выполнения команды спустя {e.timeout}с. Подробности в журнале ниже.",
            "logs": "\n".join(logs),
        }
    except Exception as e:
        logger.exception("Неожиданная ошибка")
        return {
            "type": "error",
            "message": f"Неожиданная ошибка: {e}",
        }
    finally:
        try:
            os.remove('/tmp/u-boot-sunxi-with-spl.bin')
        except:
            pass
        try:
            # Освобождаем блокировку, если она была захвачена
            if 'acquired' in locals() and acquired:
                flash_lock.release()
        except Exception:
            # Не должны падать на этапе освобождения блокировки
            pass

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        result = flash_uboot()
    return render_template_string(HTML_TEMPLATE, result=result)

@app.route('/status', methods=['GET'])
def status():
    """Простой статус: идёт ли прошивка сейчас."""
    running = flash_lock.locked()
    resp = jsonify({"running": running})
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

if __name__ == '__main__':
    logger.info("Запуск Umdu SPI U-Boot Flasher")
    # Отключаем предупреждения Flask
    import logging as flask_logging
    flask_logging.getLogger('werkzeug').setLevel(flask_logging.ERROR)
    app.run(host='0.0.0.0', port=8099, debug=False, threaded=True)
