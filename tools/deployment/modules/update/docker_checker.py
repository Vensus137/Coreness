"""
Модуль для проверки доступности Docker и docker-compose
"""

import subprocess
from typing import Dict, Optional


class DockerChecker:
    """Класс для проверки Docker и docker-compose"""
    
    def __init__(self, logger, config: Optional[Dict] = None):
        """Инициализация проверяльщика Docker"""
        self.logger = logger
        self.config = config or {}
    
    def _get_timeout(self, timeout_name: str, default: int) -> int:
        """Получает таймаут из конфига или возвращает дефолтное значение"""
        timeouts = self.config.get('deploy_settings', {}).get('timeouts', {})
        return timeouts.get(timeout_name, default)
    
    def check_docker(self) -> bool:
        """Проверяет Docker"""
        try:
            timeout = self._get_timeout('docker_info', 5)
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            if result.returncode == 0:
                self.logger.info(f"Docker найден: {result.stdout.strip()}")
                return True
            return False
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.logger.error("Docker не найден")
            return False
    
    def check_docker_compose(self) -> bool:
        """Проверяет docker-compose"""
        try:
            timeout = self._get_timeout('docker_info', 5)
            # Пробуем docker compose (новый синтаксис)
            result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            if result.returncode == 0:
                self.logger.info(f"docker compose найден: {result.stdout.strip()}")
                return True
            
            # Пробуем docker-compose (старый синтаксис)
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            if result.returncode == 0:
                self.logger.info(f"docker-compose найден: {result.stdout.strip()}")
                return True
            
            return False
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.logger.error("docker-compose не найден")
            return False
    
    def is_docker_running(self) -> bool:
        """Проверяет работу Docker daemon"""
        try:
            timeout = self._get_timeout('docker_info', 5)
            subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                check=True,
                timeout=timeout
            )
            return True
        except Exception:
            return False
    
    def get_compose_command(self) -> list:
        """Возвращает команду docker-compose"""
        # Пробуем новый синтаксис
        try:
            timeout = self._get_timeout('docker_info', 2)
            subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                check=True,
                timeout=timeout
            )
            return ['docker', 'compose']
        except Exception:
            # Fallback на старый синтаксис
            return ['docker-compose']

