# Руководство по установке российских SSL сертификатов

## 📋 Обзор

Данное руководство описывает процесс установки российских SSL сертификатов, необходимых для работы с API SaluteSpeech и другими российскими сервисами.

### ✅ Готовые сертификаты в проекте

**Хорошие новости!** В проекте уже есть готовый файл российских сертификатов:
- 📁 `ssl_certificates/russian_certs.pem` — объединенный файл всех необходимых сертификатов

**Если файл есть** — ничего устанавливать не нужно, все должно работать сразу!

**Если файла нет** — используйте автоматическую утилиту для его создания.

### Проблема
При работе с российскими API (SaluteSpeech, Yandex Cloud и др.) могут возникать SSL ошибки:
```
SSLCertVerificationError: certificate verify failed: self-signed certificate in certificate chain
```

Это происходит потому, что российские сертификаты не включены в стандартные наборы сертификатов Python/Windows.

---

## 🚀 Автоматическая установка (Рекомендуется)

### Проверка наличия сертификатов

Сначала проверьте, есть ли уже готовые сертификаты:

```bash
# Проверяем наличие файла сертификатов
ls ssl_certificates/russian_certs.pem

# Если файл есть — все готово!
# Если файла нет — читайте дальше
```

### Использование утилиты установки

В проекте есть автоматическая утилита для создания сертификатов:

```bash
# Проверка текущего состояния SSL
python tools/ssl_certificates_installer.py --test-only

# Автоматическая установка (если файла нет)
python tools/ssl_certificates_installer.py

# Принудительная переустановка
python tools/ssl_certificates_installer.py --force
```

**Что делает утилита:**
- ✅ Скачивает актуальные сертификаты с официального сайта
- ✅ Объединяет все сертификаты в один файл `russian_certs.pem`
- ✅ Автоматически проверяет SSL соединение
- ✅ Очищает все временные файлы
- ✅ Оставляет только готовый к использованию файл

**Результат:** В папке `ssl_certificates/` остается только один файл `russian_certs.pem`

---

## 🖥️ Windows (Ручная установка)

### Метод 1: Установка через PowerShell (Рекомендуется)

#### Шаг 1: Скачивание сертификатов
```powershell
# Создаем папку для сертификатов
New-Item -ItemType Directory -Path "C:\ssl-certs" -Force

# Скачиваем российские сертификаты с официального сайта
Invoke-WebRequest -Uri "https://gu-st.ru/content/lending/russian_trusted_sub_ca.zip" -OutFile "C:\ssl-certs\russian_trusted_sub_ca.zip"
Invoke-WebRequest -Uri "https://gu-st.ru/content/lending/windows_russian_trusted_root_ca.zip" -OutFile "C:\ssl-certs\russian_trusted_root_ca.zip"

# Распаковываем архивы
Expand-Archive -Path "C:\ssl-certs\russian_trusted_sub_ca.zip" -DestinationPath "C:\ssl-certs\sub_ca" -Force
Expand-Archive -Path "C:\ssl-certs\russian_trusted_root_ca.zip" -DestinationPath "C:\ssl-certs\root_ca" -Force
```

#### Шаг 2: Установка в Windows Certificate Store
```powershell
# Импортируем сертификаты в Windows (требуются права администратора)
# Находим .cer файлы в распакованных архивах
$sub_ca_cert = Get-ChildItem -Path "C:\ssl-certs\sub_ca" -Filter "*.cer" | Select-Object -First 1
$root_ca_cert = Get-ChildItem -Path "C:\ssl-certs\root_ca" -Filter "*.cer" | Select-Object -First 1

Import-Certificate -FilePath $sub_ca_cert.FullName -CertStoreLocation "Cert:\LocalMachine\Root"
Import-Certificate -FilePath $root_ca_cert.FullName -CertStoreLocation "Cert:\LocalMachine\Root"
```

#### Шаг 3: Перезапуск Python
```powershell
# Перезапустите Python/IDE после установки сертификатов
```

### Метод 2: Установка через certutil

```powershell
# Установка через certutil (требуются права администратора)
# Находим .cer файлы в распакованных архивах
$sub_ca_cert = Get-ChildItem -Path "C:\ssl-certs\sub_ca" -Filter "*.cer" | Select-Object -First 1
$root_ca_cert = Get-ChildItem -Path "C:\ssl-certs\root_ca" -Filter "*.cer" | Select-Object -First 1

certutil -addstore -f "ROOT" $sub_ca_cert.FullName
certutil -addstore -f "ROOT" $root_ca_cert.FullName
```

### Метод 3: Ручная установка через MMC

1. Откройте **MMC** (Win+R → `mmc`)
2. **Файл** → **Добавить/удалить оснастку**
3. Выберите **Сертификаты** → **Добавить**
4. Выберите **Локальный компьютер**
5. Разверните **Доверенные корневые центры сертификации** → **Сертификаты**
6. **Действие** → **Все задачи** → **Импорт**
7. Выберите скачанные `.pem` файлы

---

## 🐧 Ubuntu/Debian (Ручная установка)

### Установка через apt

```bash
# Обновляем пакеты
sudo apt update

# Устанавливаем ca-certificates
sudo apt install ca-certificates wget

# Скачиваем российские сертификаты
sudo wget -O /tmp/russian_trusted_sub_ca.zip \
  https://gu-st.ru/content/lending/russian_trusted_sub_ca.zip

sudo wget -O /tmp/russian_trusted_root_ca.zip \
  https://gu-st.ru/content/lending/windows_russian_trusted_root_ca.zip

# Распаковываем архивы
sudo unzip -o /tmp/russian_trusted_sub_ca.zip -d /tmp/sub_ca/
sudo unzip -o /tmp/russian_trusted_root_ca.zip -d /tmp/root_ca/

# Копируем .cer файлы в папку сертификатов
sudo cp /tmp/sub_ca/*.cer /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt
sudo cp /tmp/root_ca/*.cer /usr/local/share/ca-certificates/russian_trusted_root_ca.crt

# Обновляем базу сертификатов
sudo update-ca-certificates

# Проверяем установку
ls -la /etc/ssl/certs/ | grep russian
```

---

## ✅ Проверка установки

### Быстрая проверка

```bash
# Проверяем наличие файла сертификатов
ls ssl_certificates/russian_certs.pem

# Если файл есть — сертификаты готовы к использованию!
```

### Тест SSL соединения

```python
import ssl
import socket
from pathlib import Path

def test_ssl_connection():
    hostname = 'smartspeech.sber.ru'
    port = 443
    
    # Проверяем наличие сертификатов
    certs_path = Path("ssl_certificates/russian_certs.pem")
    if not certs_path.exists():
        print("❌ Файл сертификатов не найден")
        print("Запустите: python tools/ssl_certificates_installer.py")
        return False
    
    try:
        # Создаем SSL контекст с российскими сертификатами
        context = ssl.create_default_context()
        context.load_verify_locations(cafile=str(certs_path))
        
        with socket.create_connection((hostname, port)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                print(f"✅ SSL соединение успешно установлено")
                print(f"Сертификат: {cert['subject']}")
                return True
    except ssl.SSLCertVerificationError as e:
        print(f"❌ SSL ошибка: {e}")
        return False

# Запускаем тест
test_ssl_connection()
```

**Или используйте автоматическую проверку:**
```bash
python tools/ssl_certificates_installer.py --test-only
```

---

## 🔧 Устранение неполадок

### Проблема: Файл сертификатов не найден

```bash
# Проверяем наличие файла
ls ssl_certificates/russian_certs.pem

# Если файла нет — создаем его
python tools/ssl_certificates_installer.py
```

### Проблема: SSL ошибки при работе с API

```bash
# Проверяем SSL соединение
python tools/ssl_certificates_installer.py --test-only

# Если тест не проходит — переустанавливаем сертификаты
python tools/ssl_certificates_installer.py --force
```

### Проблема: Python не видит сертификаты

```python
import ssl
from pathlib import Path

# Проверяем наличие файла сертификатов
certs_path = Path("ssl_certificates/russian_certs.pem")
print(f"Файл сертификатов существует: {certs_path.exists()}")

# Проверяем SSL контекст
context = ssl.create_default_context()
if certs_path.exists():
    context.load_verify_locations(cafile=str(certs_path))
    print("✅ Сертификаты загружены в SSL контекст")
else:
    print("❌ Файл сертификатов не найден")
```

### Проблема: Все методы не работают

1. **Проверьте интернет-соединение** - сертификаты скачиваются с официального сайта
2. **Проверьте права доступа** - папка `ssl_certificates/` должна быть доступна для записи
3. **Перезапустите Python/IDE** после установки сертификатов
4. **Проверьте антивирус** - может блокировать скачивание файлов

---

## 📝 Примечания

1. **Безопасность**: Российские сертификаты официально поддерживаются государством
2. **Простота**: Сертификаты хранятся в одном файле `russian_certs.pem` в папке проекта
3. **Портативность**: Файл сертификатов можно копировать между проектами
4. **Обновления**: Сертификаты могут обновляться, используйте `--force` для переустановки
5. **Тестирование**: Всегда тестируйте в dev-среде перед продакшеном
6. **Автоматизация**: Используйте `tools/ssl_certificates_installer.py` для быстрого создания сертификатов

---

## 🔗 Полезные ссылки

- [Официальный сайт российских сертификатов (Госуслуги)](https://www.gosuslugi.ru/crt)
- [Скачивание российских сертификатов](https://gu-st.ru/content/lending/)
- [Документация certifi](https://certifi.readthedocs.io/)
- [Документация Python SSL](https://docs.python.org/3/library/ssl.html) 