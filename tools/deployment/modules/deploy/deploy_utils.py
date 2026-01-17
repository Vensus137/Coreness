"""
Утилиты для деплоя: управление версиями, временными директориями, очистка
"""

import os
import shutil
import subprocess
import tempfile
import time
from typing import Optional


class TempDirectoryManager:
    """Управление временными директориями с поддержкой context manager"""
    
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
        self.temp_dir: Optional[str] = None
    
    def __enter__(self):
        """Context manager entry - создает временную директорию"""
        self.create()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - гарантированно очищает временную директорию"""
        self.cleanup()
        return False  # Не подавляем исключения
    
    def create(self) -> str:
        """Создает временную директорию для клонирования"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                self.logger.warning(f"Не удалось удалить старую временную директорию: {e}")
        
        # Используем настройку из конфига или системную временную директорию
        temp_dir_config = self.config.get('deploy_settings', {}).get('temp_directory')
        
        if temp_dir_config:
            try:
                # Проверяем, существует ли директория
                if not os.path.exists(temp_dir_config):
                    self.logger.info(f"Создаем директорию: {temp_dir_config}")
                    print(f"📁 Создаем директорию: {temp_dir_config}")
                
                # Создаем директорию если не существует
                os.makedirs(temp_dir_config, exist_ok=True)
                
                # Проверяем права на запись
                if not os.access(temp_dir_config, os.W_OK):
                    raise PermissionError(f"Нет прав на запись в директорию: {temp_dir_config}")
                
                self.temp_dir = tempfile.mkdtemp(prefix="deploy_", dir=temp_dir_config)
                self.logger.info(f"Используем настроенную временную директорию: {self.temp_dir}")
                
            except Exception as e:
                self.logger.warning(f"Ошибка с настроенной директорией {temp_dir_config}: {e}")
                print(f"⚠️ Ошибка с настроенной директорией: {e}")
                print("💡 Используем системную временную директорию")
                
                # Fallback на системную временную директорию
                self.temp_dir = tempfile.mkdtemp(prefix="deploy_")
                self.logger.info(f"Используем системную временную директорию: {self.temp_dir}")
        else:
            # Используем системную временную директорию
            self.temp_dir = tempfile.mkdtemp(prefix="deploy_")
            self.logger.info(f"Используем системную временную директорию: {self.temp_dir}")
        
        self.logger.debug(f"Создана временная директория: {self.temp_dir}")
        return self.temp_dir
    
    def cleanup(self):
        """Очищает временные файлы"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                # Закрываем все файловые дескрипторы
                import gc
                gc.collect()
                
                # Пробуем удалить с задержкой
                time.sleep(3)
                
                # Принудительно закрываем все файлы в директории
                CleanupUtils.force_close_files(self.temp_dir, self.logger)
                
                # Дополнительная задержка после закрытия файлов
                time.sleep(2)
                
                # Пробуем удалить
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.logger.debug("Временные файлы очищены")
                
                # Проверяем, что директория действительно удалена
                if os.path.exists(self.temp_dir):
                    self.logger.warning(f"Не удалось полностью удалить: {self.temp_dir}")
                    # Пробуем принудительное удаление через Windows API
                    success = CleanupUtils.force_delete_directory(self.temp_dir, self.logger)
                    
                    # Финальная проверка после принудительного удаления
                    if success and not os.path.exists(self.temp_dir):
                        self.logger.info(f"Временная директория успешно удалена: {self.temp_dir}")
                    elif not os.path.exists(self.temp_dir):
                        self.logger.info(f"Временная директория успешно удалена: {self.temp_dir}")
                    else:
                        self.logger.warning(f"Временная директория НЕ удалена и осталась на диске: {self.temp_dir}")
                else:
                    self.logger.info(f"Временная директория успешно удалена: {self.temp_dir}")
                    
            except Exception as e:
                self.logger.warning(f"Ошибка очистки временных файлов: {e}")


class VersionManager:
    """Управление версиями для деплоя"""
    
    @staticmethod
    def validate_version_format(version: str) -> bool:
        """Проверяет формат версии (например, 3.0.5)"""
        parts = version.split('.')
        if len(parts) == 3:
            try:
                int(parts[0])  # major
                int(parts[1])  # minor
                int(parts[2])  # patch
                return True
            except ValueError:
                return False
        return False


class CleanupUtils:
    """Утилиты для очистки файлов и процессов"""
    
    @staticmethod
    def force_delete_directory(path: str, logger) -> bool:
        """Принудительное удаление директории через Windows API"""
        try:
            # Нормализуем путь (убираем смешанные слеши)
            normalized_path = os.path.normpath(path)
            
            # Пробуем удалить через rmdir /s /q с правильным экранированием пути
            try:
                # Используем list с путем как отдельным аргументом (без кавычек, subprocess сам экранирует)
                result = subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', normalized_path], 
                                      capture_output=True, text=True, timeout=15, encoding='cp866')
                
                # Проверяем фактическое удаление, а не код возврата
                time.sleep(0.5)  # Даем время файловой системе обновиться
                if not os.path.exists(normalized_path):
                    logger.info(f"Директория удалена через Windows API: {normalized_path}")
                    return True
                else:
                    error_msg = result.stderr.strip() if result.stderr else f"Код возврата: {result.returncode}"
                    logger.warning(f"Не удалось удалить через Windows API: {error_msg}")
                    
            except (UnicodeDecodeError, UnicodeError):
                # Если проблема с кодировкой, пробуем без capture_output
                try:
                    result = subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', normalized_path], 
                                          timeout=15)
                    # Проверяем фактическое удаление
                    time.sleep(0.5)
                    if not os.path.exists(normalized_path):
                        logger.info(f"Директория удалена через Windows API (без вывода): {normalized_path}")
                        return True
                    else:
                        logger.warning(f"Не удалось удалить через Windows API (код: {result.returncode})")
                except Exception as e:
                    logger.debug(f"Ошибка Windows API без вывода: {e}")
            
            # Альтернативный метод через PowerShell
            try:
                # Экранируем одинарные кавычки в пути (удваиваем их для PowerShell)
                escaped_path = normalized_path.replace("'", "''")
                # Используем одинарные кавычки в PowerShell для избежания проблем с экранированием
                ps_command = f"Remove-Item -Path '{escaped_path}' -Recurse -Force -ErrorAction SilentlyContinue"
                result = subprocess.run(['powershell', '-Command', ps_command], 
                                      capture_output=True, text=True, timeout=15, encoding='utf-8')
                
                # Проверяем фактическое удаление
                time.sleep(0.5)
                if not os.path.exists(normalized_path):
                    logger.info(f"Директория удалена через PowerShell: {normalized_path}")
                    return True
                else:
                    error_msg = result.stderr.strip() if result.stderr else f"Директория все еще существует (код: {result.returncode})"
                    if error_msg:  # Логируем только если есть сообщение об ошибке
                        logger.warning(f"Не удалось удалить через PowerShell: {error_msg}")
                    
            except Exception as e:
                logger.debug(f"Ошибка PowerShell: {e}")
            
            # Последняя попытка - через shutil с повторными попытками
            try:
                for _attempt in range(3):
                    time.sleep(1)
                    if not os.path.exists(normalized_path):
                        logger.info(f"Директория удалена (проверка существования): {normalized_path}")
                        return True
                    try:
                        shutil.rmtree(normalized_path, ignore_errors=True)
                        if not os.path.exists(normalized_path):
                            logger.info(f"Директория удалена через shutil: {normalized_path}")
                            return True
                    except Exception:
                        pass
                logger.debug(f"Не удалось удалить директорию через shutil после 3 попыток: {normalized_path}")
            except Exception as e:
                logger.debug(f"Ошибка shutil: {e}")
                
            return False
                
        except Exception as e:
            logger.debug(f"Ошибка принудительного удаления: {e}")
            return False
    
    @staticmethod
    def force_close_files(path: str, logger):
        """Принудительно закрывает все файлы в директории"""
        try:
            import psutil

            # Получаем все процессы, которые могут использовать файлы
            for proc in psutil.process_iter(['pid', 'open_files', 'name']):
                try:
                    if proc.info['open_files']:
                        for file_info in proc.info['open_files']:
                            if path in file_info.path:
                                logger.debug(f"Процесс {proc.info['pid']} ({proc.info['name']}) использует файл: {file_info.path}")
                                
                                # Если это Git процесс или Python процесс, пробуем его завершить
                                if any(keyword in proc.info['name'].lower() for keyword in ['git', 'python']):
                                    logger.debug(f"Завершаем процесс: {proc.info['pid']}")
                                    try:
                                        proc.terminate()
                                        proc.wait(timeout=3)
                                    except psutil.TimeoutExpired:
                                        proc.kill()
                                        logger.debug(f"Принудительно завершен процесс: {proc.info['pid']}")
                                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
            # Дополнительная задержка после завершения процессов
            time.sleep(2)
                        
        except ImportError:
            # psutil не установлен, пропускаем
            pass
        except Exception as e:
            logger.debug(f"Ошибка при проверке открытых файлов: {e}")

