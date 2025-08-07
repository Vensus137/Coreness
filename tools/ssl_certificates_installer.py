#!/usr/bin/env python3
"""
Утилита для автоматической установки российских SSL сертификатов в проект

Скачивает сертификаты прямо в папку проекта и настраивает их для использования.
"""

import os
import sys
import platform
import subprocess
import urllib.request
import ssl
import socket
import shutil
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager
    from plugins.utilities.foundation.logger.logger import Logger
    from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
except ImportError:
    print("❌ Не удалось импортировать утилиты проекта")
    print("Убедитесь, что вы запускаете скрипт из корня проекта")
    sys.exit(1)


class SSLCertificatesInstaller:
    """Установщик российских SSL сертификатов в проект"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.cert_urls = {
            'sub_ca': 'https://gu-st.ru/content/lending/russian_trusted_sub_ca.zip',
            'root_ca': 'https://gu-st.ru/content/lending/windows_russian_trusted_root_ca.zip'
        }
        
        # Инициализируем утилиты проекта
        self.logger = Logger()
        self.plugins_manager = PluginsManager(logger=self.logger)
        self.settings_manager = SettingsManager(logger=self.logger, plugins_manager=self.plugins_manager)
        
        # Определяем корень проекта
        self.project_root = self._get_project_root()
        self.certs_dir = self.project_root / 'ssl_certificates'
        self.certs_dir.mkdir(exist_ok=True)
        
        # Путь к объединенному файлу сертификатов
        self.combined_certs_path = self.certs_dir / 'russian_certs.pem'
    
    def _get_project_root(self):
        """Определяет корень проекта используя метод из settings_manager"""
        return self.settings_manager.get_project_root()
    
    def print_header(self):
        """Выводит заголовок утилиты"""
        print("🔐 Установщик российских SSL сертификатов в проект")
        print("=" * 60)
        print(f"Система: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}")
        print(f"Корень проекта: {self.project_root}")
        print(f"Папка сертификатов: {self.certs_dir}")
        print()
    
    def download_certificates(self):
        """Скачивает российские сертификаты в папку проекта"""
        print("📥 Скачивание сертификатов в проект...")
        
        downloaded_files = []
        
        for cert_type, url in self.cert_urls.items():
            zip_path = self.certs_dir / f"russian_trusted_{cert_type}.zip"
            
            try:
                print(f"  Скачиваю {cert_type}...")
                urllib.request.urlretrieve(url, zip_path)
                print(f"  ✅ {cert_type} скачан: {zip_path}")
                
                # Распаковываем архив
                extract_dir = self.certs_dir / cert_type
                extract_dir.mkdir(exist_ok=True)
                
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Ищем .cer файлы в распакованном архиве
                cer_files = list(extract_dir.glob("*.cer"))
                if cer_files:
                    downloaded_files.extend(cer_files)
                    print(f"  ✅ Найдено {len(cer_files)} сертификатов в {cert_type}")
                else:
                    print(f"  ⚠️ Сертификаты не найдены в {cert_type}")
                    
                # Также добавляем все .cer файлы из всех подпапок
                for subdir in extract_dir.iterdir():
                    if subdir.is_dir():
                        sub_cer_files = list(subdir.glob("*.cer"))
                        if sub_cer_files:
                            downloaded_files.extend(sub_cer_files)
                            print(f"  ✅ Найдено {len(sub_cer_files)} дополнительных сертификатов в {subdir.name}")
                    
            except Exception as e:
                print(f"  ❌ Ошибка скачивания {cert_type}: {e}")
                return False
        
        # Создаем объединенный файл сертификатов
        if self._create_combined_cert_file(downloaded_files):
            print(f"  ✅ Создан объединенный файл: {self.combined_certs_path}")
        
        return True
    
    def _create_combined_cert_file(self, cert_files):
        """Создает объединенный файл сертификатов"""
        try:
            with open(self.combined_certs_path, 'w', encoding='utf-8') as combined_file:
                for cert_file in cert_files:
                    # Читаем .cer файл как текстовый (он уже в PEM формате)
                    try:
                        with open(cert_file, 'r', encoding='utf-8') as f:
                            cert_content = f.read()
                    except UnicodeDecodeError:
                        # Если UTF-8 не работает, пробуем другие кодировки
                        with open(cert_file, 'r', encoding='latin-1') as f:
                            cert_content = f.read()
                    
                    # Добавляем сертификат в объединенный файл
                    combined_file.write(cert_content)
                    combined_file.write('\n')  # Добавляем разделитель
            
            self.logger.info(f"Создан объединенный файл сертификатов: {self.combined_certs_path}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка создания объединенного файла: {e}")
            return False
    
    def install_windows(self):
        """Устанавливает сертификаты в Windows Certificate Store"""
        print("🖥️ Установка в Windows Certificate Store...")
        
        # Проверяем права администратора
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            
            if not is_admin:
                print("  ⚠️ Требуются права администратора!")
                print("  Запустите PowerShell от имени администратора и выполните:")
                print(f"  python {sys.argv[0]}")
                print()
                print("  Или используйте альтернативный метод через MMC")
                return False
        except:
            pass
        
        # Устанавливаем через certutil
        success = False
        for cert_type in ['sub_ca', 'root_ca']:
            cert_dir = self.certs_dir / cert_type
            if cert_dir.exists():
                for cert_file in cert_dir.glob("*.cer"):
                    try:
                        print(f"  Устанавливаю {cert_file.name}...")
                        result = subprocess.run(
                            ['certutil', '-addstore', '-f', 'ROOT', str(cert_file)],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        print(f"  ✅ {cert_file.name} установлен")
                        success = True
                    except subprocess.CalledProcessError as e:
                        print(f"  ❌ Ошибка установки {cert_file.name}: {e}")
        
        return success
    
    def install_ubuntu(self):
        """Устанавливает сертификаты в Ubuntu/Debian"""
        print("🐧 Установка в Ubuntu/Debian...")
        
        try:
            # Копируем сертификаты в системную папку
            for cert_file in self.certs_dir.glob("russian_trusted_*.pem"):
                system_cert_path = f"/usr/local/share/ca-certificates/{cert_file.stem}.crt"
                
                print(f"  Копирую {cert_file.name} в {system_cert_path}...")
                shutil.copy2(cert_file, system_cert_path)
            
            # Обновляем базу сертификатов
            print("  Обновляю базу сертификатов...")
            subprocess.run(['sudo', 'update-ca-certificates'], check=True)
            
            print("  ✅ Сертификаты установлены в систему")
            return True
            
        except Exception as e:
            print(f"  ❌ Ошибка установки: {e}")
            return False
    
    def test_ssl_connection(self):
        """Тестирует SSL соединение с российскими серверами"""
        print("🧪 Тестирование SSL соединения...")
        
        test_hosts = [
            ('smartspeech.sber.ru', 443),
            ('ngw.devices.sberbank.ru', 9443),
        ]
        
        all_success = True
        
        for hostname, port in test_hosts:
            print(f"  Тестирую {hostname}:{port}...")
            
            try:
                # Создаем SSL контекст с нашими сертификатами
                context = ssl.create_default_context()
                if self.combined_certs_path.exists():
                    context.load_verify_locations(cafile=str(self.combined_certs_path))
                
                # Тестируем соединение
                with socket.create_connection((hostname, port), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        print(f"  ✅ {hostname}:{port} - SSL соединение успешно")
                        print(f"     Сертификат: {cert['subject']}")
            except ssl.SSLCertVerificationError as e:
                print(f"  ❌ {hostname}:{port} - SSL ошибка сертификата: {e}")
                all_success = False
            except Exception as e:
                print(f"  ❌ {hostname}:{port} - Ошибка соединения: {e}")
                all_success = False
        
        return all_success
    
    def cleanup(self):
        """Очищает временные файлы после установки"""
        try:
            print("🧹 Очистка временных файлов...")
            
            # Удаляем ZIP архивы
            for cert_type in ['sub_ca', 'root_ca']:
                zip_path = self.certs_dir / f"russian_trusted_{cert_type}.zip"
                if zip_path.exists():
                    zip_path.unlink()
                    print(f"  ✅ Удален: {zip_path.name}")
            
            # Удаляем папки с распакованными сертификатами
            for cert_type in ['sub_ca', 'root_ca']:
                cert_dir = self.certs_dir / cert_type
                if cert_dir.exists():
                    shutil.rmtree(cert_dir)
                    print(f"  ✅ Удалена папка: {cert_type}/")
            
            # Удаляем конфигурационный файл (больше не нужен)
            config_path = self.certs_dir / 'ssl_config.py'
            if config_path.exists():
                config_path.unlink()
                print(f"  ✅ Удален: ssl_config.py")
            
            print("  ✅ Очистка завершена")
            
        except Exception as e:
            print(f"⚠️ Ошибка очистки: {e}")
    
    def install(self, force=False):
        """Основной метод установки"""
        self.print_header()
        
        # Проверяем, не установлены ли уже сертификаты
        if not force and self.combined_certs_path.exists():
            print("ℹ️ Сертификаты уже установлены в проекте")
            print(f"   Путь: {self.combined_certs_path}")
            
            if self.test_ssl_connection():
                print("✅ SSL соединение работает корректно!")
                return True
            else:
                print("⚠️ SSL соединение не работает, переустанавливаем...")
        
        # Скачиваем сертификаты
        if not self.download_certificates():
            print("❌ Ошибка скачивания сертификатов")
            return False
        
        # Устанавливаем в систему (опционально)
        if self.system == 'windows':
            self.install_windows()
        elif self.system == 'linux':
            self.install_ubuntu()
        
        # Тестируем соединение
        if self.test_ssl_connection():
            print("✅ SSL сертификаты успешно установлены и работают!")
            return True
        else:
            print("⚠️ SSL сертификаты установлены, но соединение не работает")
            print("   Возможно, требуется перезапуск Python/IDE")
            return False


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Установщик российских SSL сертификатов')
    parser.add_argument('--test-only', action='store_true', help='Только тестирование без установки')
    parser.add_argument('--force', action='store_true', help='Принудительная переустановка')
    
    args = parser.parse_args()
    
    installer = SSLCertificatesInstaller()
    
    if args.test_only:
        print("🧪 Только тестирование SSL соединения")
        installer.test_ssl_connection()
    else:
        installer.install(force=args.force)
    
    installer.cleanup()


if __name__ == "__main__":
    main() 