"""
Модуль для работы с Docker образами
Сборка, тегирование, откат, очистка образов
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class ImageManager:
    """Класс для работы с Docker образами"""
    
    def __init__(self, project_root: Path, logger, config: Optional[Dict] = None, compose_manager=None, container_manager=None):
        """Инициализация менеджера образов"""
        self.project_root = project_root
        self.logger = logger
        self.config = config or {}
        self.compose_manager = compose_manager
        self.container_manager = container_manager
    
    def _get_timeout(self, timeout_name: str, default: int) -> int:
        """Получает таймаут из конфига или возвращает дефолтное значение"""
        timeouts = self.config.get('deploy_settings', {}).get('timeouts', {})
        return timeouts.get(timeout_name, default)
    
    def build_with_compose(self, environment: str = "test", version: Optional[str] = None, compose_command: List = None) -> bool:
        """
        Собирает Docker образ через docker-compose
        Для prod окружения тегирует образ версией для возможности отката
        """
        try:
            if not self.compose_manager:
                self.logger.error("ComposeManager не установлен")
                return False
            
            if not compose_command:
                self.logger.error("Команда docker-compose не установлена")
                return False
            
            # Используем ту же логику, что и restart_with_compose - получаем все compose файлы
            # Это нужно для правильной работы с extends
            compose_file = None
            if self.container_manager:
                base_config, env_config, override_config = self.container_manager._get_compose_files(environment)
                if not base_config or not env_config:
                    self.logger.error(f"Не удалось найти compose файлы для окружения {environment}")
                    return False
                
                # Строим команду с нужными файлами
                cmd_files = ['-f', str(base_config), '-f', str(env_config)]
                if override_config:
                    cmd_files.extend(['-f', str(override_config)])
                # Используем base_config для определения рабочего каталога
                compose_file = base_config
            else:
                # Fallback на старую логику (для обратной совместимости)
                compose_file = self.compose_manager.get_compose_file(environment)
                if not compose_file or not compose_file.exists():
                    self.logger.error(f"Файл docker-compose не найден: {compose_file}")
                    return False
                cmd_files = ['-f', str(compose_file)]
            
            # Для глобальных compose файлов нужно использовать правильный рабочий каталог
            # Если compose файл в ~/.docker-compose/, используем project_root как cwd
            # Иначе используем docker/ директорию
            if compose_file and str(compose_file).startswith(str(Path.home() / ".docker-compose")):
                # Глобальный compose файл - используем project_root
                build_cwd = self.project_root
            else:
                # Локальный compose файл - используем docker/ директорию
                build_cwd = self.project_root / "docker"
            
            cmd = compose_command + cmd_files + ['build']
            
            timeout = self._get_timeout('docker_build', 600)
            self.logger.info(f"Сборка Docker образа для окружения {environment}")
            result = subprocess.run(
                cmd,
                cwd=build_cwd,
                capture_output=False,
                timeout=timeout
            )
            
            if result.returncode == 0:
                self.logger.info("Docker образ успешно собран")
                
                # Для prod тегируем образ версией после сборки
                if environment == "prod" and version:
                    if self.tag_image(compose_file, version):
                        self.logger.info(f"Образ тегирован версией: {version}")
                    else:
                        self.logger.warning("Не удалось тегировать образ версией (не критично)")
                
                return True
            else:
                self.logger.error(f"Ошибка сборки Docker образа (код: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Таймаут при сборке Docker образа")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка сборки Docker образа: {e}")
            return False
    
    def tag_image(self, compose_file: Path, version: str) -> bool:
        """Тегирует собранный образ версией"""
        try:
            if not self.compose_manager:
                return False
            
            image_id = self.compose_manager.get_built_image_id(compose_file)
            if not image_id:
                self.logger.warning("Не удалось определить ID собранного образа")
                return False
            
            image_name = self.compose_manager.get_image_name(compose_file)
            if not image_name:
                self.logger.warning("Не удалось определить имя образа")
                return False
            
            # Тегируем образ версией и latest
            for tag in [version, 'latest']:
                tag_cmd = ['docker', 'tag', image_id, f"{image_name}:{tag}"]
                timeout = self._get_timeout('git_operation', 30)
                result = subprocess.run(
                    tag_cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=timeout
                )
                
                if result.returncode != 0:
                    self.logger.warning(f"Не удалось тегировать образ тегом {tag}: {result.stderr}")
                    return False
            
            self.logger.info(f"Образ тегирован: {image_name}:{version} и {image_name}:latest")
            return True
            
        except Exception as e:
            self.logger.warning(f"Ошибка тегирования образа: {e}")
            return False
    
    def rollback_image(self, environment: str, version: str, compose_command: List = None, container_manager=None) -> bool:
        """
        Откатывает Docker образ на указанную версию (только для prod)
        """
        if environment != "prod":
            self.logger.warning("Откат образа доступен только для prod окружения")
            return False
        
        try:
            if not self.compose_manager:
                self.logger.error("ComposeManager не установлен")
                return False
            
            compose_file = self.compose_manager.get_compose_file(environment)
            if not compose_file or not compose_file.exists():
                self.logger.error(f"Файл docker-compose не найден: {compose_file}")
                return False
            
            image_name = self.compose_manager.get_image_name(compose_file)
            if not image_name:
                self.logger.error("Не удалось определить имя образа")
                return False
            
            # Проверяем существование образа с указанной версией
            timeout = self._get_timeout('docker_info', 10)
            check_cmd = ['docker', 'images', '-q', f"{image_name}:{version}"]
            result = subprocess.run(
                check_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            if not result.stdout.strip():
                self.logger.error(f"Образ {image_name}:{version} не найден")
                return False
            
            if not compose_command:
                self.logger.error("Команда docker-compose не установлена")
                return False
            
            # Останавливаем контейнеры
            if container_manager:
                container_manager.stop_with_compose(environment)
            else:
                self.logger.info(f"Остановка контейнеров для отката на версию {version}")
                timeout_stop = self._get_timeout('docker_stop', 60)
                stop_cmd = compose_command + [
                    '-f', str(compose_file),
                    'down'
                ]
                subprocess.run(
                    stop_cmd,
                    cwd=self.project_root / "docker",
                    capture_output=False,
                    timeout=timeout_stop
                )
            
            # Обновляем тег latest на нужную версию
            timeout_tag = self._get_timeout('git_operation', 30)
            tag_cmd = ['docker', 'tag', f"{image_name}:{version}", f"{image_name}:latest"]
            result = subprocess.run(
                tag_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout_tag
            )
            
            if result.returncode != 0:
                self.logger.error(f"Ошибка тегирования образа: {result.stderr}")
                return False
            
            # Запускаем контейнеры с откатанным образом
            if container_manager:
                return container_manager.restart_with_compose(environment)
            else:
                timeout_rollback = self._get_timeout('docker_rollback', 120)
                self.logger.info(f"Запуск контейнеров с версией {version}")
                up_cmd = compose_command + [
                    '-f', str(compose_file),
                    'up', '-d', '--force-recreate'
                ]
                result = subprocess.run(
                    up_cmd,
                    cwd=self.project_root / "docker",
                    capture_output=False,
                    timeout=timeout_rollback
                )
                
                if result.returncode == 0:
                    self.logger.info(f"Откат на версию {version} выполнен успешно")
                    return True
                else:
                    self.logger.error(f"Ошибка отката образа (код: {result.returncode})")
                    return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Таймаут при откате образа")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка отката образа: {e}")
            return False
    
    def list_available_versions(self, environment: str) -> list:
        """
        Возвращает список доступных версий образов (только для prod)
        """
        if environment != "prod":
            return []
        
        try:
            if not self.compose_manager:
                return []
            
            compose_file = self.compose_manager.get_compose_file(environment)
            image_name = self.compose_manager.get_image_name(compose_file)
            if not image_name:
                return []
            
            # Получаем список тегов образа
            timeout = self._get_timeout('docker_info', 10)
            cmd = ['docker', 'images', '--format', '{{.Tag}}', image_name]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            if result.returncode != 0:
                return []
            
            tags = [tag.strip() for tag in result.stdout.strip().split('\n') if tag.strip() and tag.strip() != 'latest']
            # Сортируем версии
            tags.sort(key=lambda x: tuple(map(int, x.split('.'))) if x.replace('.', '').isdigit() else (0, 0, 0))
            return tags
            
        except Exception as e:
            self.logger.warning(f"Ошибка получения списка версий: {e}")
            return []
    
    def list_images_with_info(self, environment: str) -> list:
        """
        Возвращает список образов с информацией (версия, размер, дата создания)
        """
        images = []
        try:
            if not self.compose_manager:
                return []
            
            compose_file = self.compose_manager.get_compose_file(environment)
            image_name = self.compose_manager.get_image_name(compose_file)
            if not image_name:
                return []
            
            # Получаем список образов с информацией
            timeout = self._get_timeout('docker_info', 10)
            cmd = ['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedAt}}', image_name]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            if result.returncode != 0:
                return []
            
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    full_name = parts[0]
                    size = parts[1]
                    created = parts[2]
                    # Извлекаем версию из полного имени
                    if ':' in full_name:
                        version = full_name.split(':')[1]
                        if version != 'latest':
                            images.append({
                                'version': version,
                                'size': size,
                                'created': created,
                                'full_name': full_name
                            })
            
            # Сортируем по версии (новые первыми)
            def version_key(x):
                try:
                    # Пробуем парсить версию как числа
                    parts = x['version'].replace('-beta', '').replace('-alpha', '').split('.')
                    return tuple(int(p) for p in parts if p.isdigit())
                except (ValueError, KeyError, AttributeError):
                    return (0, 0, 0)
            
            images.sort(key=version_key, reverse=True)
            return images
            
        except Exception as e:
            self.logger.error(f"Ошибка получения списка образов: {e}")
            return []
    
    def cleanup_old_images(self, environment: str = "prod", keep_versions: int = 5, versions_to_remove: Optional[list] = None) -> dict:
        """
        Очищает старые Docker образы
        Возвращает словарь с результатами очистки
        """
        result = {
            "dangling_removed": 0,
            "old_versions_removed": 0,
            "space_freed": 0,
            "errors": []
        }
        
        try:
            # 1. Удаляем dangling images (неиспользуемые промежуточные образы)
            self.logger.info("Очистка dangling images...")
            dangling_cmd = ['docker', 'image', 'prune', '-f']
            dangling_result = subprocess.run(
                dangling_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            
            if dangling_result.returncode == 0:
                # Парсим вывод для подсчета удаленных образов
                output = dangling_result.stdout
                if "Total reclaimed space:" in output:
                    # Извлекаем размер
                    match = re.search(r'Total reclaimed space: ([\d.]+)(\w+)', output)
                    if match:
                        size = float(match.group(1))
                        unit = match.group(2)
                        # Конвертируем в байты для единообразия
                        multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
                        result["space_freed"] += int(size * multipliers.get(unit, 1))
                result["dangling_removed"] = 1  # Флаг успешной очистки
                self.logger.info("Dangling images очищены")
            else:
                result["errors"].append(f"Ошибка очистки dangling images: {dangling_result.stderr}")
            
            # 2. Удаляем старые версии образов (только для prod)
            if environment == "prod" and self.compose_manager:
                compose_file = self.compose_manager.get_compose_file(environment)
                if compose_file and compose_file.exists():
                    image_name = self.compose_manager.get_image_name(compose_file)
                    if image_name:
                        # Если указаны конкретные версии для удаления - используем их
                        if versions_to_remove:
                            old_versions = versions_to_remove
                        else:
                            # Получаем список всех версий
                            versions = self.list_available_versions(environment)
                            
                            if len(versions) > keep_versions:
                                # Сортируем версии (новые первыми)
                                def version_sort_key(x):
                                    try:
                                        # Убираем суффиксы типа -beta, -alpha
                                        clean = x.replace('-beta', '').replace('-alpha', '').replace('-', '.')
                                        parts = clean.split('.')
                                        return tuple(int(p) for p in parts if p.isdigit())
                                    except (ValueError, AttributeError):
                                        return (0, 0, 0)
                                
                                versions.sort(key=version_sort_key, reverse=True)
                                
                                # Удаляем старые версии (оставляем последние keep_versions)
                                old_versions = versions[keep_versions:]
                            else:
                                old_versions = []
                        
                        if old_versions:
                            for version in old_versions:
                                try:
                                    # Получаем размер образа перед удалением
                                    timeout = self._get_timeout('docker_info', 10)
                                    size_cmd = ['docker', 'images', '--format', '{{.Size}}', f"{image_name}:{version}"]
                                    size_result = subprocess.run(
                                        size_cmd,
                                        capture_output=True,
                                        text=True,
                                        encoding='utf-8',
                                        errors='replace',
                                        timeout=timeout
                                    )
                                    
                                    image_size = 0
                                    if size_result.returncode == 0 and size_result.stdout.strip():
                                        # Парсим размер (формат: "123MB" или "1.2GB")
                                        size_str = size_result.stdout.strip()
                                        size_match = re.match(r'([\d.]+)(\w+)', size_str)
                                        if size_match:
                                            size_val = float(size_match.group(1))
                                            size_unit = size_match.group(2)
                                            multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
                                            image_size = int(size_val * multipliers.get(size_unit, 1))
                                    
                                    timeout = self._get_timeout('git_operation', 30)
                                    self.logger.info(f"Удаление образа {image_name}:{version}")
                                    rm_cmd = ['docker', 'rmi', '-f', f"{image_name}:{version}"]
                                    rm_result = subprocess.run(
                                        rm_cmd,
                                        capture_output=True,
                                        text=True,
                                        encoding='utf-8',
                                        errors='replace',
                                        timeout=timeout
                                    )
                                    
                                    if rm_result.returncode == 0:
                                        result["old_versions_removed"] += 1
                                        result["space_freed"] += image_size
                                    else:
                                        # Проверяем, не ошибка ли это из-за того, что образ используется
                                        if "image is being used" in rm_result.stderr.lower() or "image is referenced" in rm_result.stderr.lower():
                                            result["errors"].append(f"Образ {image_name}:{version} используется и не может быть удален")
                                        else:
                                            result["errors"].append(f"Не удалось удалить {image_name}:{version}: {rm_result.stderr}")
                                except Exception as e:
                                    result["errors"].append(f"Ошибка при удалении {image_name}:{version}: {e}")
                        
                        if not versions_to_remove and not old_versions:
                            versions = self.list_available_versions(environment)
                            self.logger.info(f"Все версии сохранены (всего {len(versions)}, требуется сохранить {keep_versions})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка очистки образов: {e}")
            result["errors"].append(str(e))
            return result

