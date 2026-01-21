import re
from typing import Any, Dict, List, Optional, Union

from openai import AsyncOpenAI


class AIClient:
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.data_converter = kwargs.get('data_converter')
        
        # Get settings
        self.settings = self.settings_manager.get_plugin_settings('ai_client')
        
        # Settings from config.yaml
        self.api_key = self.settings.get("api_key", "")
        self.base_url = self.settings.get("base_url", "https://api.polza.ai/v1")
        self.default_model = self.settings.get("default_model")
        self.max_tokens = self.settings.get("max_tokens", 200)
        self.temperature = self.settings.get("temperature", 0.7)
        self.default_embedding_model = self.settings.get("default_embedding_model", "text-embedding-3-small")
        self.default_embedding_dimensions = self.settings.get("default_embedding_dimensions", 1024)
        
        # Initialize OpenAI client
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
        Completion via AI API (Polza.ai, OpenRouter, etc.)
        Corresponds to /v1/chat/completions endpoint
        """
        try:
            # Prepare parameters
            model = model or self.default_model
            max_tokens = max_tokens or self.max_tokens
            temperature = temperature or self.temperature
            
            # Determine which client to use
            client_to_use = self.client
            if api_key and api_key != self.api_key:
                # Create temporary client with passed token
                client_to_use = AsyncOpenAI(
                    api_key=api_key,
                    base_url=self.base_url
                )
            
            # Build response_format for JSON modes
            response_format = self._build_response_format(json_mode, json_schema)
            
            # Build messages for API
            messages = self._build_messages(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context,
                json_mode=json_mode,
                rag_chunks=rag_chunks,
                chunk_format=chunk_format
            )
            
            # Parameters for API request
            api_params = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Add response_format if specified
            if response_format:
                api_params["response_format"] = response_format
            
            # Add tools if specified
            if tools:
                api_params["tools"] = tools
            
            # Add tool_choice if specified
            if tool_choice:
                api_params["tool_choice"] = tool_choice
            
            # Call AI API via OpenAI SDK (use appropriate client)
            response = await client_to_use.chat.completions.create(**api_params)
            
            # Get model response
            message = response.choices[0].message
            response_content = message.content or ""
            
            # Get tool_calls if model called functions
            # Note: usually model returns either tool_calls or content, but not both simultaneously.
            # If model decided to call function, content is usually None.
            # However, some models may return both content and tool_calls simultaneously.
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
            
            # Parse JSON string to dict if json_mode is used
            parsed_dict = None
            if json_mode and response_content and self.data_converter:
                try:
                    # Clean response from markdown code blocks (```json ... ```)
                    cleaned_content = response_content.strip()
                    if cleaned_content.startswith("```"):
                        # Remove opening ```json or ```
                        lines = cleaned_content.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        # Remove closing ```
                        if lines and lines[-1].strip() == "```":
                            lines = lines[:-1]
                        cleaned_content = "\n".join(lines)
                    
                    # Use data_converter to parse JSON string to dict
                    parsed_dict = await self.data_converter.convert_string_to_type(cleaned_content)
                    # Check that we got dict or list (valid JSON)
                    if not isinstance(parsed_dict, (dict, list)):
                        parsed_dict = None
                except Exception as e:
                    self.logger.warning(f"Failed to parse JSON response to dict: {e}")
            
            # Form result
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
            
            # Add parsed dict if exists
            if parsed_dict is not None:
                result["response_data"]["response_dict"] = parsed_dict
            
            # Add tool_calls if model called functions
            if tool_calls:
                result["response_data"]["tool_calls"] = tool_calls
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
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
        Build response_format for JSON modes
        """
        if not json_mode:
            return None
        
        if json_mode == "json_schema":
            if not json_schema:
                self.logger.warning("json_mode='json_schema' specified, but json_schema not provided. Using json_object.")
                return {"type": "json_object"}
            return {
                "type": "json_schema",
                "json_schema": json_schema
            }
        elif json_mode == "json_object":
            return {"type": "json_object"}
        else:
            self.logger.warning(f"Unknown json_mode: {json_mode}. Using json_object.")
            return {"type": "json_object"}
    
    def _build_messages(self, prompt: str, system_prompt: str = "", context: str = "",
                       json_mode: Optional[str] = None, rag_chunks: Optional[List[Dict[str, Any]]] = None,
                       chunk_format: Optional[Dict[str, str]] = None) -> list:
        """
        Build messages for AI API with RAG support
        
        Messages format:
        1. system (instructions)
        2. Dialog (user→assistant pairs from chat_history, sorted by created_at)
        3. Final user with context (knowledge + other + custom context) + question
        """
        messages = []
        
        # Group chunks by types and roles
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
                
                # Apply chunk format if template specified for this type
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
        
        # 1. System message
        system_content = ""
        if system_prompt:
            system_content = system_prompt
        
        if system_content:
            messages.append({
                "role": "system",
                "content": system_content
            })
        
        # 2. Dialog (chat_history) - sort by created_at to preserve order
        if chat_history_chunks:
            # Sort by created_at (oldest first) for correct history order
            # created_at - real message creation date, used for correct sorting
            # Also use processed_at, chunk_index and document_id for determinism
            def sort_key(chunk):
                # created_at - required field in DB (NOT NULL), always present
                # Multi-level sorting corresponds to DB sorting
                created_at = chunk.get("created_at", "")
                processed_at = chunk.get("processed_at", "")
                chunk_index = chunk.get("chunk_index", 0)
                document_id = chunk.get("document_id", "")
                
                # ISO strings sort lexicographically correctly
                # Combine for multi-level sorting (like in DB)
                return (created_at, processed_at, chunk_index, document_id)
            
            chat_history_chunks.sort(key=sort_key)
            
            for chunk in chat_history_chunks:
                messages.append({
                    "role": chunk["role"],
                    "content": chunk["content"]
                })
        
        # 3. Final user with context (knowledge + other + custom context) + question
        final_user_content = ""
        
        # Add knowledge chunks
        if knowledge_chunks:
            # Calculate average similarity
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
        
        # Add other chunks and custom context to ADD. CONTEXT
        additional_context_parts = []
        
        # Collect other chunks
        if other_chunks:
            for i, chunk in enumerate(other_chunks, 1):
                additional_context_parts.append(f"[{i}] {chunk['content']}")
        
        # Add custom context (if specified)
        if context:
            additional_context_parts.append(context)
        
        # Form ADD. CONTEXT block if there's something to add
        if additional_context_parts:
            additional_context_text = "ADD. CONTEXT:\n" + "\n".join(additional_context_parts) + "\n\n"
            final_user_content += additional_context_text
        
        # Add question
        if final_user_content:
            final_user_content += f"QUESTION: {prompt}"
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
        Apply chunk format to content if template specified for document type
        """
        if not chunk_format:
            return content
        
        # Get template for document type
        template = chunk_format.get(chunk_type)
        if not template:
            return content
        
        # Apply template
        return self._apply_chunk_template(template, content, chunk)
    
    def _apply_chunk_template(self, template: str, content: str, chunk: Dict[str, Any]) -> str:
        """
        Apply template with $ markers to chunk data
        Available: $content (required) + any fields from chunk_metadata
        Supports fallback: $field|fallback:value
        """
        # Form data dict: content + chunk_metadata
        chunk_metadata = chunk.get("chunk_metadata") or {}
        chunk_data = {
            "content": content,
            **chunk_metadata
        }
        
        # Pattern for markers: $key or $key|fallback:value
        # Problem: determine fallback boundaries (where value ends)
        # Solution: fallback is word or phrase, limited by ] } ) , space before $ or end of line
        # Use greedy quantifier, but stop at certain characters
        
        # Pattern: $key or $key|fallback:value
        # Fallback ends on: ] } ) space+$ or end of line
        # Use [\w\sА-Яа-я]+ for fallback (words and spaces), but stop at special characters
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
        Generate embedding for text via AI API (Polza.ai, OpenRouter, etc.)
        
        Note: dimensions parameter is supported only for OpenAI text-embedding-3-small 
        and text-embedding-3-large. For other models (Cohere, HuggingFace, etc.) dimension is fixed.
        """
        try:
            # Use default settings if not specified
            model = model or self.default_embedding_model
            dimensions = dimensions if dimensions is not None else self.default_embedding_dimensions
            
            # Determine which client to use
            client_to_use = self.client
            if api_key and api_key != self.api_key:
                # Create temporary client with passed token
                client_to_use = AsyncOpenAI(
                    api_key=api_key,
                    base_url=self.base_url
                )
            
            # Prepare parameters for API
            api_params = {
                "model": model,
                "input": text
            }
            
            # dimensions parameter supported only for OpenAI text-embedding-3 models
            # For other models (Cohere, HuggingFace, etc.) don't pass dimensions
            if "text-embedding-3" in model.lower():
                api_params["dimensions"] = dimensions
            
            # Call embeddings API
            response = await client_to_use.embeddings.create(**api_params)
            
            # Get embedding
            embedding_data = response.data[0]
            embedding_vector = embedding_data.embedding
            
            # Form result (flat structure like in completion)
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
            self.logger.error(f"Error generating embedding: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "API_ERROR",
                    "message": str(e)
                }
            }
    
    def shutdown(self):
        """Properly close client and all connections"""
        try:
            if hasattr(self.client, 'close') and self.client:
                import asyncio
                try:
                    # Try to close client in existing event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, create task for closing
                        loop.create_task(self.client.close())
                    else:
                        # If loop not running, run it for closing
                        loop.run_until_complete(self.client.close())
                except RuntimeError:
                    # If no event loop, create new one
                    asyncio.run(self.client.close())
                except Exception as e:
                    self.logger.warning(f"Error closing AI client: {e}")
        except Exception as e:
            self.logger.warning(f"Error during AI client shutdown: {e}")
