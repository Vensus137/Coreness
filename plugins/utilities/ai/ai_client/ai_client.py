import re
from typing import Any, Dict, List, Optional, Union

from openai import AsyncOpenAI


class AIClient:
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.data_converter = kwargs.get('data_converter')
        
        # Получаем настройки
        self.settings = self.settings_manager.get_plugin_settings('ai_client')
        
        # Настройки из config.yaml
        self.api_key = self.settings.get("api_key", "")
        self.base_url = self.settings.get("base_url", "https://api.polza.ai/v1")
        self.default_model = self.settings.get("default_model")
        self.max_tokens = self.settings.get("max_tokens", 200)
        self.temperature = self.settings.get("temperature", 0.7)
        self.default_embedding_model = self.settings.get("default_embedding_model", "text-embedding-3-small")
        self.default_embedding_dimensions = self.settings.get("default_embedding_dimensions", 1024)
        
        # Инициализация OpenAI клиента
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    async def completion(self, prompt: str, system_prompt: str = "", model: Optional[str] = None, 
                           max_tokens: Optional[int] = None, temperature: Optional[float] = None, 
                           context: str = "", json_mode: Optional[str] = None, 
                           json_schema: Optional[Dict[str, Any]] = None,
                           tools: Optional[List[Dict[str, Any]]] = None,
                           tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
                           api_key: Optional[str] = None,
                           rag_chunks: Optional[List[Dict[str, Any]]] = None,
                           chunk_format: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Completion через AI API (Polza.ai, OpenRouter и др.)
        Соответствует эндпоинту /v1/chat/completions
        """
        try:
            # Подготовка параметров
            model = model or self.default_model
            max_tokens = max_tokens or self.max_tokens
            temperature = temperature or self.temperature
            
            # Определяем какой клиент использовать
            client_to_use = self.client
            if api_key and api_key != self.api_key:
                # Создаем временный клиент с переданным токеном
                client_to_use = AsyncOpenAI(
                    api_key=api_key,
                    base_url=self.base_url
                )
            
            # Построение response_format для JSON режимов
            response_format = self._build_response_format(json_mode, json_schema)
            
            # Построение сообщений для API
            messages = self._build_messages(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context,
                json_mode=json_mode,
                rag_chunks=rag_chunks,
                chunk_format=chunk_format
            )
            
            # Параметры для API запроса
            api_params = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Добавляем response_format если указан
            if response_format:
                api_params["response_format"] = response_format
            
            # Добавляем tools если указаны
            if tools:
                api_params["tools"] = tools
            
            # Добавляем tool_choice если указан
            if tool_choice:
                api_params["tool_choice"] = tool_choice
            
            # Вызов AI API через OpenAI SDK (используем нужный клиент)
            response = await client_to_use.chat.completions.create(**api_params)
            
            # Получаем ответ модели
            message = response.choices[0].message
            response_content = message.content or ""
            
            # Получаем tool_calls если модель вызвала функции
            # Примечание: обычно модель возвращает либо tool_calls, либо content, но не оба одновременно.
            # Если модель решила вызвать функцию, content обычно будет None.
            # Однако некоторые модели могут вернуть и content и tool_calls одновременно.
            tool_calls = None
            if message.tool_calls:
                tool_calls = [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    for tool_call in message.tool_calls
                ]
            
            # Парсим JSON строку в словарь если используется json_mode
            parsed_dict = None
            if json_mode and response_content and self.data_converter:
                try:
                    # Очищаем ответ от markdown код-блоков (```json ... ```)
                    cleaned_content = response_content.strip()
                    if cleaned_content.startswith("```"):
                        # Убираем открывающий ```json или ```
                        lines = cleaned_content.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        # Убираем закрывающий ```
                        if lines and lines[-1].strip() == "```":
                            lines = lines[:-1]
                        cleaned_content = "\n".join(lines)
                    
                    # Используем data_converter для парсинга JSON строки в словарь
                    parsed_dict = await self.data_converter.convert_string_to_type(cleaned_content)
                    # Проверяем, что получили словарь или список (валидный JSON)
                    if not isinstance(parsed_dict, (dict, list)):
                        parsed_dict = None
                except Exception as e:
                    self.logger.warning(f"Не удалось распарсить JSON ответ в словарь: {e}")
            
            # Формируем результат
            result = {
                "result": "success",
                "response_data": {
                    "response_completion": response_content,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "model": model
                }
            }
            
            # Добавляем распарсенный словарь если есть
            if parsed_dict is not None:
                result["response_data"]["response_dict"] = parsed_dict
            
            # Добавляем tool_calls если модель вызвала функции
            if tool_calls:
                result["response_data"]["tool_calls"] = tool_calls
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации ответа: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "API_ERROR",
                    "message": str(e)
                }
            }
    
    def _build_response_format(self, json_mode: Optional[str], 
                               json_schema: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Построение response_format для JSON режимов
        """
        if not json_mode:
            return None
        
        if json_mode == "json_schema":
            if not json_schema:
                self.logger.warning("json_mode='json_schema' указан, но json_schema не предоставлен. Используется json_object.")
                return {"type": "json_object"}
            return {
                "type": "json_schema",
                "json_schema": json_schema
            }
        elif json_mode == "json_object":
            return {"type": "json_object"}
        else:
            self.logger.warning(f"Неизвестный json_mode: {json_mode}. Используется json_object.")
            return {"type": "json_object"}
    
    def _build_messages(self, prompt: str, system_prompt: str = "", context: str = "",
                       json_mode: Optional[str] = None, rag_chunks: Optional[List[Dict[str, Any]]] = None,
                       chunk_format: Optional[Dict[str, str]] = None) -> list:
        """
        Построение сообщений для AI API с поддержкой RAG
        
        Формат messages:
        1. system (инструкции)
        2. Диалог (user→assistant пары из chat_history, отсортированные по created_at)
        3. Финальный user с контекстом (knowledge + other + кастомный context) + вопрос
        """
        messages = []
        
        # Группируем чанки по типам и ролям
        chat_history_chunks = []
        knowledge_chunks = []
        other_chunks = []
        
        if rag_chunks:
            for chunk in rag_chunks:
                chunk_type = chunk.get("document_type", "other")
                chunk_role = chunk.get("role", "user")
                chunk_content = chunk.get("content", "")
                chunk_created_at = chunk.get("created_at")
                chunk_processed_at = chunk.get("processed_at")
                chunk_index = chunk.get("chunk_index", 0)
                chunk_document_id = chunk.get("document_id", "")
                
                # Применяем формат чанка, если указан шаблон для этого типа
                formatted_content = self._apply_chunk_format(chunk_content, chunk, chunk_type, chunk_format)
                
                if chunk_type == "chat_history":
                    chat_history_chunks.append({
                        "role": chunk_role,
                        "content": formatted_content,
                        "created_at": chunk_created_at,
                        "processed_at": chunk_processed_at,
                        "chunk_index": chunk_index,
                        "document_id": chunk_document_id
                    })
                elif chunk_type == "knowledge":
                    knowledge_chunks.append({
                        "content": formatted_content,
                        "similarity": chunk.get("similarity"),
                        "document_id": chunk.get("document_id")
                    })
                elif chunk_type == "other":
                    other_chunks.append({
                        "content": formatted_content
                    })
        
        # 1. Системное сообщение
        system_content = ""
        if system_prompt:
            system_content = system_prompt
        
        if system_content:
            messages.append({
                "role": "system",
                "content": system_content
            })
        
        # 2. Диалог (chat_history) - сортируем по created_at для сохранения порядка
        if chat_history_chunks:
            # Сортируем по created_at (старые первыми) для правильного порядка истории
            # created_at - реальная дата создания сообщения, используется для корректной сортировки
            # Также используем processed_at, chunk_index и document_id для детерминированности
            def sort_key(chunk):
                # created_at - обязательное поле в БД (NOT NULL), всегда присутствует
                # Многоуровневая сортировка соответствует сортировке в БД
                created_at = chunk.get("created_at", "")
                processed_at = chunk.get("processed_at", "")
                chunk_index = chunk.get("chunk_index", 0)
                document_id = chunk.get("document_id", "")
                
                # ISO строки сортируются лексикографически корректно
                # Комбинируем для многоуровневой сортировки (как в БД)
                return (created_at, processed_at, chunk_index, document_id)
            
            chat_history_chunks.sort(key=sort_key)
            
            for chunk in chat_history_chunks:
                messages.append({
                    "role": chunk["role"],
                    "content": chunk["content"]
                })
        
        # 3. Финальный user с контекстом (knowledge + other + кастомный context) + вопрос
        final_user_content = ""
        
        # Добавляем knowledge чанки
        if knowledge_chunks:
            # Вычисляем среднюю similarity
            similarities = [c.get("similarity") for c in knowledge_chunks if c.get("similarity") is not None]
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0
            
            knowledge_text = "KNOWLEDGE"
            if len(knowledge_chunks) > 1:
                knowledge_text += f" ({len(knowledge_chunks)}, avg: {avg_similarity:.2f}):"
            else:
                if avg_similarity > 0:
                    knowledge_text += f" (avg: {avg_similarity:.2f}):"
                else:
                    knowledge_text += ":"
            knowledge_text += "\n"
            
            for i, chunk in enumerate(knowledge_chunks, 1):
                similarity = chunk.get("similarity")
                similarity_str = f"{similarity:.2f} " if similarity is not None else ""
                knowledge_text += f"[{i}] {similarity_str}{chunk['content']}\n"
            
            final_user_content += knowledge_text + "\n"
        
        # Добавляем other чанки и кастомный контекст в ДОП. КОНТЕКСТ
        additional_context_parts = []
        
        # Собираем other чанки
        if other_chunks:
            for i, chunk in enumerate(other_chunks, 1):
                additional_context_parts.append(f"[{i}] {chunk['content']}")
        
        # Добавляем кастомный контекст (если указан)
        if context:
            additional_context_parts.append(context)
        
        # Формируем блок ДОП. КОНТЕКСТ если есть что добавить
        if additional_context_parts:
            additional_context_text = "ДОП. КОНТЕКСТ:\n" + "\n".join(additional_context_parts) + "\n\n"
            final_user_content += additional_context_text
        
        # Добавляем вопрос
        if final_user_content:
            final_user_content += f"ВОПРОС: {prompt}"
        else:
            final_user_content = prompt
        
        messages.append({
            "role": "user",
            "content": final_user_content
        })
        
        return messages
    
    def _apply_chunk_format(self, content: str, chunk: Dict[str, Any], chunk_type: str,
                           chunk_format: Optional[Dict[str, str]]) -> str:
        """
        Применяет формат чанка к контенту, если указан шаблон для типа документа
        """
        if not chunk_format:
            return content
        
        # Получаем шаблон для типа документа
        template = chunk_format.get(chunk_type)
        if not template:
            return content
        
        # Применяем шаблон
        return self._apply_chunk_template(template, content, chunk)
    
    def _apply_chunk_template(self, template: str, content: str, chunk: Dict[str, Any]) -> str:
        """
        Применяет шаблон с маркерами $ к данным чанка
        Доступны: $content (обязательно) + любые поля из chunk_metadata
        Поддерживает fallback: $field|fallback:значение
        """
        # Формируем словарь данных: content + chunk_metadata
        chunk_metadata = chunk.get("chunk_metadata") or {}
        chunk_data = {
            "content": content,
            **chunk_metadata
        }
        
        # Паттерн для маркеров: $key или $key|fallback:value
        # Проблема: определить границы fallback (где заканчивается значение)
        # Решение: fallback — это слово или фраза, ограниченная ] } ) , пробелом перед $ или концом строки
        # Используем жадный квантификатор, но останавливаемся на определенных символах
        
        # Паттерн: $key или $key|fallback:value
        # Fallback заканчивается на: ] } ) пробел+$ или конец строки
        # Используем [\w\sА-Яа-я]+ для fallback (слова и пробелы), но останавливаемся на спецсимволах
        pattern = r'\$(\w+)(?:\|fallback:([\w\sА-Яа-яЁё]+))?'
        
        def replace_placeholder(match):
            key = match.group(1)
            fallback = match.group(2) if match.group(2) else None
            
            value = chunk_data.get(key)
            if value is None or value == '':
                return fallback if fallback else ''
            
            return str(value)
        
        result = re.sub(pattern, replace_placeholder, template)
        return result
    
    async def embedding(self, text: str, model: Optional[str] = None, 
                       dimensions: Optional[int] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Генерация embedding для текста через AI API (Polza.ai, OpenRouter и др.)
        
        Примечание: параметр dimensions поддерживается только для OpenAI text-embedding-3-small 
        и text-embedding-3-large. Для других моделей (Cohere, HuggingFace и др.) размерность фиксирована.
        """
        try:
            # Используем настройки по умолчанию если не указаны
            model = model or self.default_embedding_model
            dimensions = dimensions if dimensions is not None else self.default_embedding_dimensions
            
            # Определяем какой клиент использовать
            client_to_use = self.client
            if api_key and api_key != self.api_key:
                # Создаем временный клиент с переданным токеном
                client_to_use = AsyncOpenAI(
                    api_key=api_key,
                    base_url=self.base_url
                )
            
            # Подготавливаем параметры для API
            api_params = {
                "model": model,
                "input": text
            }
            
            # Параметр dimensions поддерживается только для OpenAI text-embedding-3 моделей
            # Для других моделей (Cohere, HuggingFace и др.) не передаем dimensions
            if "text-embedding-3" in model.lower():
                api_params["dimensions"] = dimensions
            
            # Вызов embeddings API
            response = await client_to_use.embeddings.create(**api_params)
            
            # Получаем embedding
            embedding_data = response.data[0]
            embedding_vector = embedding_data.embedding
            
            # Формируем результат (плоская структура как в completion)
            result = {
                "result": "success",
                "response_data": {
                    "embedding": embedding_vector,
                    "model": model,
                    "dimensions": len(embedding_vector),
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации embedding: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "API_ERROR",
                    "message": str(e)
                }
            }
    
    def shutdown(self):
        """Корректное закрытие клиента и всех соединений"""
        try:
            if hasattr(self.client, 'close') and self.client:
                import asyncio
                try:
                    # Пытаемся закрыть клиент в существующем event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Если loop запущен, создаем задачу для закрытия
                        loop.create_task(self.client.close())
                    else:
                        # Если loop не запущен, запускаем его для закрытия
                        loop.run_until_complete(self.client.close())
                except RuntimeError:
                    # Если нет event loop, создаем новый
                    asyncio.run(self.client.close())
                except Exception as e:
                    self.logger.warning(f"Ошибка закрытия AI клиента: {e}")
        except Exception as e:
            self.logger.warning(f"Ошибка при shutdown AI клиента: {e}")
