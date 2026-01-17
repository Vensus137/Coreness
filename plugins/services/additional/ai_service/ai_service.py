from typing import Any, Dict


class AIService:
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.ai_client = kwargs['ai_client']
        self.settings_manager = kwargs['settings_manager']
        self.database_manager = kwargs['database_manager']
        self.task_manager = kwargs['task_manager']
        
        # Получаем настройки
        self.settings = self.settings_manager.get_plugin_settings('ai_service')
        self.allow_default_api_key = self.settings.get('allow_default_api_key', False)
        
        # Получаем утилиту id_generator через DI
        self.id_generator = kwargs['id_generator']
        
        # Получаем datetime_formatter через DI для парсинга дат
        self.datetime_formatter = kwargs.get('datetime_formatter')
        
        # Условная инициализация RAG модулей из extension (если доступны)
        self.text_processor = None
        self.vector_storage_manager = None
        self.embedding_generator = None
        
        try:
            from .extension.text_processor import TextProcessor  # type: ignore
            from .extension.embedding_generator import EmbeddingGenerator  # type: ignore
            from .extension.vector_storage_manager import VectorStorageManager  # type: ignore
            
            self.text_processor = TextProcessor(logger=self.logger)
            
            self.embedding_generator = EmbeddingGenerator(
                logger=self.logger,
                ai_client=self.ai_client,
                task_manager=self.task_manager
            )
            
            self.vector_storage_manager = VectorStorageManager(
                logger=self.logger,
                database_manager=self.database_manager,
                text_processor=self.text_processor,
                embedding_generator=self.embedding_generator,
                id_generator=self.id_generator,
                ai_client=self.ai_client,
                settings=self.settings,
                datetime_formatter=self.datetime_formatter
            )
            
            self.logger.info("Extension модули загружены успешно")
        except ImportError:
            self.logger.info("Extension модули не найдены - часть функций может быть недоступна")
        
        # Регистрируем себя в ActionHub
        self.action_hub = kwargs['action_hub']
        self.action_hub.register('ai_service', self)
    
    def _get_api_key(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получение и валидация API ключа из конфига тенанта или дефолтного
        Возвращает dict с 'api_key' при успехе или dict с 'result': 'error' при ошибке
        """
        # Получаем токен из конфига тенанта (_config)
        tenant_config = data.get('_config', {})
        api_key = tenant_config.get('ai_token') if tenant_config else None
        
        # Валидация токена
        if not api_key:
            if not self.allow_default_api_key:
                return {
                    "result": "error",
                    "error": {
                        "code": "MISSING_API_KEY",
                        "message": "AI API ключ не установлен для тенанта. Установите токен через действие update_tenant_config или в файле config.yaml"
                    }
                }
            # Используем дефолтный токен (только если разрешено)
            api_key = self.ai_client.api_key
            if not api_key:
                return {
                    "result": "error",
                    "error": {
                        "code": "MISSING_API_KEY",
                        "message": "AI API ключ не установлен ни для тенанта, ни в настройках ai_client"
                    }
                }
        
        return {"api_key": api_key}
    
    async def completion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI completion через ИИ
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Извлечение параметров из данных
            prompt = data.get("prompt", "")
            system_prompt = data.get("system_prompt", "")
            context = data.get("context", "")  # Кастомный контекст (добавляется в финальное user сообщение)
            model = data.get("model")
            max_tokens = data.get("max_tokens")
            temperature = data.get("temperature")
            json_mode = data.get("json_mode")
            json_schema = data.get("json_schema")
            tools = data.get("tools")
            tool_choice = data.get("tool_choice")
            rag_chunks = data.get("rag_chunks")  # Массив чанков из RAG поиска
            chunk_format = data.get("chunk_format")  # Формат отображения чанков
            
            # Получаем и валидируем токен
            api_key_result = self._get_api_key(data)
            if api_key_result.get("result") == "error":
                return api_key_result
            api_key = api_key_result["api_key"]
            
            # Вызов утилиты для AI completion с токеном
            ai_response = await self.ai_client.completion(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode,
                json_schema=json_schema,
                tools=tools,
                tool_choice=tool_choice,
                api_key=api_key,  # Передаем токен
                rag_chunks=rag_chunks,  # Передаем чанки для RAG
                chunk_format=chunk_format  # Передаем формат чанков
            )
            
            # Возвращаем ответ утилиты как есть (уже в стандартном формате)
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Ошибка в AI Service: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка сервиса: {str(e)}"
                }
            }
    
    async def embedding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерация embedding для текста через ИИ
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Извлечение параметров из данных
            text = data.get("text", "")
            model = data.get("model")
            dimensions = data.get("dimensions")
            
            # Получаем и валидируем токен
            api_key_result = self._get_api_key(data)
            if api_key_result.get("result") == "error":
                return api_key_result
            api_key = api_key_result["api_key"]
            
            # Вызов утилиты для генерации embedding с токеном
            ai_response = await self.ai_client.embedding(
                text=text,
                model=model,
                dimensions=dimensions,
                api_key=api_key  # Передаем токен
            )
            
            # Возвращаем ответ утилиты как есть (уже в стандартном формате)
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Ошибка в AI Service (embedding): {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка сервиса: {str(e)}"
                }
            }
    
    async def save_embedding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сохранение текста в vector_storage с автоматическим разбиением на чанки и генерацией embeddings
        """
        if not self.vector_storage_manager:
            return {
                "result": "error",
                "error": {
                    "code": "FEATURE_NOT_AVAILABLE",
                    "message": "Функция недоступна. Extension модули не найдены."
                }
            }
        
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Извлечение параметров из данных
            text = data.get("text", "")
            document_id = data.get("document_id")
            document_type = data.get("document_type")
            role = data.get("role", "user")  # По умолчанию 'user'
            chunk_metadata = data.get("chunk_metadata")  # Метаданные чанка (chat_id, username и др.)
            model = data.get("model")
            dimensions = data.get("dimensions", 1024)
            # Используем значения из настроек, если не указаны в параметрах
            chunk_size = data.get("chunk_size", self.settings.get("chunk_size", 512))
            chunk_overlap = data.get("chunk_overlap", self.settings.get("chunk_overlap", 100))
            replace_existing = data.get("replace_existing", False)
            generate_embedding = data.get("generate_embedding", True)  # По умолчанию true для обратной совместимости
            created_at = data.get("created_at")  # Опциональная дата создания (для правильной сортировки истории)
            
            # Получаем tenant_id из контекста (валидация выполняется централизованно в ActionRegistry)
            tenant_id = data.get('tenant_id')
            
            # Получаем и валидируем токен (требуется только если generate_embedding=true)
            api_key = None
            if generate_embedding:
                api_key_result = self._get_api_key(data)
                if api_key_result.get("result") == "error":
                    return api_key_result
                api_key = api_key_result["api_key"]
            
            # Делегируем выполнение в vector_storage_manager
            return await self.vector_storage_manager.save_embedding(
                tenant_id=tenant_id,
                text=text,
                document_id=document_id,
                document_type=document_type,
                model=model,
                dimensions=dimensions,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                replace_existing=replace_existing,
                generate_embedding=generate_embedding,
                api_key=api_key,
                role=role,
                chunk_metadata=chunk_metadata,
                created_at=created_at
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка в AI Service (save_embedding): {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка сервиса: {str(e)}"
                }
            }
    
    async def delete_embedding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Удаление данных из vector_storage по document_id или по дате processed_at
        """
        if not self.vector_storage_manager:
            return {
                "result": "error",
                "error": {
                    "code": "FEATURE_NOT_AVAILABLE",
                    "message": "Функция недоступна. Extension модули не найдены."
                }
            }
        
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Извлечение параметров из данных
            document_id = data.get("document_id")
            until_date = data.get("until_date")
            since_date = data.get("since_date")
            metadata_filter = data.get("metadata_filter")  # Фильтр по метаданным (chat_id, username и др.)
            
            # Получаем tenant_id из контекста (валидация выполняется централизованно в ActionRegistry)
            tenant_id = data.get('tenant_id')
            
            # Делегируем выполнение в vector_storage_manager
            return await self.vector_storage_manager.delete_embedding(
                tenant_id=tenant_id,
                document_id=document_id,
                until_date=until_date,
                since_date=since_date,
                metadata_filter=metadata_filter
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка в AI Service (delete_embedding): {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка сервиса: {str(e)}"
                }
            }
    
    async def search_embedding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Поиск похожих чанков по тексту или вектору (semantic search)
        """
        if not self.vector_storage_manager:
            return {
                "result": "error",
                "error": {
                    "code": "FEATURE_NOT_AVAILABLE",
                    "message": "Функция недоступна. Extension модули не найдены."
                }
            }
        
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Извлечение параметров из данных
            query_text = data.get("query_text")
            query_vector = data.get("query_vector")
            # Используем значения из настроек, если не указаны в параметрах
            limit_chunks = data.get("limit_chunks", self.settings.get("search_limit_chunks", 10))
            limit_chars = data.get("limit_chars")
            min_similarity = data.get("min_similarity", self.settings.get("search_min_similarity", 0.7))
            document_type = data.get("document_type")
            document_id = data.get("document_id")
            until_date = data.get("until_date")
            since_date = data.get("since_date")
            metadata_filter = data.get("metadata_filter")  # Фильтр по метаданным (chat_id, username и др.)
            model = data.get("model")
            dimensions = data.get("dimensions", 1024)
            
            # Получаем tenant_id из контекста (валидация выполняется централизованно в ActionRegistry)
            tenant_id = data.get('tenant_id')
            
            # Получаем и валидируем токен (нужен если передан query_text)
            api_key = None
            if query_text:
                api_key_result = self._get_api_key(data)
                if api_key_result.get("result") == "error":
                    return api_key_result
                api_key = api_key_result["api_key"]
            
            # Делегируем выполнение в vector_storage_manager
            return await self.vector_storage_manager.search_embeddings(
                tenant_id=tenant_id,
                query_text=query_text,
                query_vector=query_vector,
                limit_chunks=limit_chunks,
                limit_chars=limit_chars,
                min_similarity=min_similarity,
                document_type=document_type,
                document_id=document_id,
                metadata_filter=metadata_filter,
                model=model,
                dimensions=dimensions,
                api_key=api_key or "",  # Если query_vector, api_key не нужен
                until_date=until_date,
                since_date=since_date
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка в AI Service (search_embedding): {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка сервиса: {str(e)}"
                }
            }
    
    async def get_recent_chunks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получение последних N чанков по дате processed_at (не векторный поиск)
        """
        if not self.vector_storage_manager:
            return {
                "result": "error",
                "error": {
                    "code": "FEATURE_NOT_AVAILABLE",
                    "message": "Функция недоступна. Extension модули не найдены."
                }
            }
        
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Извлечение параметров из данных
            # Используем значения из настроек, если не указаны в параметрах
            limit_chunks = data.get("limit_chunks", self.settings.get("search_limit_chunks", 10))
            limit_chars = data.get("limit_chars")
            document_type = data.get("document_type")
            document_id = data.get("document_id")
            until_date = data.get("until_date")
            since_date = data.get("since_date")
            metadata_filter = data.get("metadata_filter")  # Фильтр по метаданным (chat_id, username и др.)
            
            # Получаем tenant_id из контекста (валидация выполняется централизованно в ActionRegistry)
            tenant_id = data.get('tenant_id')
            
            # Делегируем выполнение в vector_storage_manager
            return await self.vector_storage_manager.get_recent_chunks(
                tenant_id=tenant_id,
                limit_chunks=limit_chunks,
                limit_chars=limit_chars,
                document_type=document_type,
                document_id=document_id,
                until_date=until_date,
                since_date=since_date,
                metadata_filter=metadata_filter
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка в AI Service (get_recent_chunks): {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка сервиса: {str(e)}"
                }
            }
