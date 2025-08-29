import hashlib
import os
import time
from typing import Dict, Any

class HashManager:
    """
    Утилита для генерации хэшей из атрибутов и файлов.
    """
    
    def __init__(self, logger):
        self.logger = logger

    def generate_hash_from_attributes(self, **attributes) -> str:
        """
        Генерирует хэш из набора атрибутов с сортировкой для уникальности
        """
        try:
            # Сортируем ключи для уникальности порядка
            sorted_items = sorted(attributes.items())
            
            # Конкатенируем в строку
            hash_string = "_".join(f"{k}={v}" for k, v in sorted_items)
            
            # Генерируем MD5 (быстрее SHA256, подходит для кэширования)
            return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации хэша из атрибутов: {e}")
            raise

    def generate_hash_from_path(self, file_path: str) -> str:
        """
        Ультрабыстрый хэш файла только по пути (для кэширования)
        """
        try:
            # Просто хэшируем путь к файлу
            return hashlib.md5(file_path.encode()).hexdigest()
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации хэша пути {file_path}: {e}")
            raise

    def generate_hash(self, file_path: str = None, **attributes) -> str:
        """
        Универсальный метод генерации хэша
        Автоматически выбирает способ: путь к файлу или атрибуты
        """
        try:
            if file_path:
                # Если передан путь к файлу, генерируем хэш пути
                return self.generate_hash_from_path(file_path)
            elif attributes:
                # Если переданы атрибуты, генерируем хэш атрибутов
                return self.generate_hash_from_attributes(**attributes)
            else:
                raise ValueError("Необходимо передать либо file_path, либо атрибуты")
                
        except Exception as e:
            self.logger.error(f"Ошибка универсальной генерации хэша: {e}")
            raise

    def _generate_timestamp_code(self, length: int = 8) -> str:
        """
        Внутренний метод: генерирует timestamp-код заданной длины на основе миллисекунд
        """
        try:
            ts = int(time.time() * 1000)  # миллисекунды
            return str(ts)[-length:]
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации timestamp-кода: {e}")
            raise

    def generate_filename(self, prefix: str, extension: str = None, code_length: int = 8) -> str:
        """
        Генерирует уникальное имя файла в формате <prefix>-<code1>-<code2>.<extension>
        
        Args:
            prefix: Префикс имени файла (например, голос)
            extension: Расширение файла (mp3, opus, wav и т.д.)
            code_length: Длина кода (по умолчанию 8 для формата 4-4)
        
        Returns:
            Имя файла в формате prefix-code1-code2.extension или prefix-code1-code2
        """
        try:
            # Генерируем timestamp-код
            code = self._generate_timestamp_code(code_length)
            
            # Разбиваем код на две части (формат 4-4)
            if code_length == 8:
                code1 = code[:4]
                code2 = code[4:]
                formatted_code = f"{code1}-{code2}"
            else:
                # Для других длин используем простой дефис посередине
                mid = code_length // 2
                code1 = code[:mid]
                code2 = code[mid:]
                formatted_code = f"{code1}-{code2}"
            
            # Формируем имя файла
            if extension:
                filename = f"{prefix}-{formatted_code}.{extension}"
            else:
                filename = f"{prefix}-{formatted_code}"
            
            return filename
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации имени файла: {e}")
            raise 

    def generate_code(self, length: int = 8, use_digits: bool = True, 
                     use_letters: bool = True, random: bool = False, **attributes) -> str:
        """Генерирует код заданной длины (случайный или детерминированный)"""
        try:
            # Валидация длины
            if length < 6 or length > 16:
                raise ValueError("Длина кода должна быть от 6 до 16 символов")
            
            # Если случайная генерация, добавляем timestamp и random
            if random:
                import random as random_module
                attributes['timestamp'] = int(time.time() * 1000)
                attributes['random'] = random_module.randint(1000, 9999)
            
            # Генерируем SHA256 хеш (64 символа hex)
            hash_hex = hashlib.sha256(
                self._prepare_attributes_string(**attributes).encode()
            ).hexdigest()
            
            # Определяем набор символов
            chars = ""
            if use_letters:
                chars += "abcdefghijklmnopqrstuvwxyz"  # 26 символов
            if use_digits:
                chars += "0123456789"  # 10 символов
            
            if not chars:
                raise ValueError("Должен быть выбран хотя бы один тип символов")
            
            # Конвертируем hex в код нужной длины
            result = ""
            for i in range(length):
                # Берем по 2 символа hex за раз (1 байт)
                hex_pair = hash_hex[i * 2:(i * 2) + 2]
                # Конвертируем hex в число (0-255)
                byte_value = int(hex_pair, 16)
                # Получаем индекс символа
                char_index = byte_value % len(chars)
                result += chars[char_index]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации кода: {e}")
            raise

    def _prepare_attributes_string(self, **attributes) -> str:
        """Подготавливает строку атрибутов для хеширования"""
        sorted_items = sorted(attributes.items())
        return "_".join(f"{k}={v}" for k, v in sorted_items) 