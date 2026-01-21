from typing import Any, Dict


class AIService:
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.ai_client = kwargs['ai_client']
        self.settings_manager = kwargs['settings_manager']
        
        # Get settings
        self.settings = self.settings_manager.get_plugin_settings('ai_service')
        self.allow_default_api_key = self.settings.get('allow_default_api_key', False)
        
        # Register ourselves in ActionHub
        self.action_hub = kwargs['action_hub']
        self.action_hub.register('ai_service', self)
    
    def _get_api_key(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get and validate API key from tenant config or default
        Returns dict with 'api_key' on success or dict with 'result': 'error' on error
        """
        # Get token from tenant config (_config)
        tenant_config = data.get('_config', {})
        api_key = tenant_config.get('ai_token') if tenant_config else None
        
        # Token validation
        if not api_key:
            if not self.allow_default_api_key:
                return {
                    "result": "error",
                    "error": {
                        "code": "MISSING_API_KEY",
                        "message": "AI API key not set for tenant. Set token through update_tenant_config action or in config.yaml file"
                    }
                }
            # Use default token (only if allowed)
            api_key = self.ai_client.api_key
            if not api_key:
                return {
                    "result": "error",
                    "error": {
                        "code": "MISSING_API_KEY",
                        "message": "AI API key not set for tenant or in ai_client settings"
                    }
                }
        
        return {"api_key": api_key}
    
    async def completion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI completion through AI
        """
        try:
            # Validation is done centrally in ActionRegistry
            # Extract parameters from data
            prompt = data.get("prompt", "")
            system_prompt = data.get("system_prompt", "")
            context = data.get("context", "")  # Custom context (added to final user message)
            model = data.get("model")
            max_tokens = data.get("max_tokens")
            temperature = data.get("temperature")
            json_mode = data.get("json_mode")
            json_schema = data.get("json_schema")
            tools = data.get("tools")
            tool_choice = data.get("tool_choice")
            rag_chunks = data.get("rag_chunks")  # Array of chunks from RAG search
            chunk_format = data.get("chunk_format")  # Chunk display format
            
            # Get and validate token
            api_key_result = self._get_api_key(data)
            if api_key_result.get("result") == "error":
                return api_key_result
            api_key = api_key_result["api_key"]
            
            # Call utility for AI completion with token
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
                api_key=api_key,  # Pass token
                rag_chunks=rag_chunks,  # Pass chunks for RAG
                chunk_format=chunk_format  # Pass chunk format
            )
            
            # Return utility response as is (already in standard format)
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Error in AI Service: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal service error: {str(e)}"
                }
            }
    
    async def embedding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate embedding for text through AI
        """
        try:
            # Validation is done centrally in ActionRegistry
            # Extract parameters from data
            text = data.get("text", "")
            model = data.get("model")
            dimensions = data.get("dimensions")
            
            # Get and validate token
            api_key_result = self._get_api_key(data)
            if api_key_result.get("result") == "error":
                return api_key_result
            api_key = api_key_result["api_key"]
            
            # Call utility for embedding generation with token
            ai_response = await self.ai_client.embedding(
                text=text,
                model=model,
                dimensions=dimensions,
                api_key=api_key  # Pass token
            )
            
            # Return utility response as is (already in standard format)
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Error in AI Service (embedding): {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal service error: {str(e)}"
                }
            }
    
