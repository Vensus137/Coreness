"""
Utility for generating deterministic unique IDs through IdSequence
"""

import hashlib
import uuid
from typing import Optional


class IdGenerator:
    """
    Utility for generating deterministic unique IDs
    Returns the same ID for the same seed
    Supports caching through cache_manager
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.database_manager = kwargs['database_manager']
        self.cache_manager = kwargs['cache_manager']
        self.settings_manager = kwargs['settings_manager']
        
        # Get cache settings
        settings = self.settings_manager.get_plugin_settings('id_generator')
        self.cache_ttl = settings.get('cache_ttl', 600)  # 10 minutes by default
    
    def _calculate_hash(self, seed: str) -> str:
        """
        Calculate MD5 hash from seed
        """
        return hashlib.md5(seed.encode('utf-8')).hexdigest()
    
    def _get_cache_key(self, hash_value: str) -> str:
        """Generate cache key in cache_manager format"""
        return f"id:hash:{hash_value}"
    
    async def get_or_create_unique_id(self, seed: Optional[str] = None) -> Optional[int]:
        """
        Get or create unique ID for seed
        Returns existing ID if seed already existed, or creates new one
        
        If seed not specified, generates random UUID (saved to DB for debugging)
        Supports caching through cache_manager
        """
        try:
            # If seed not provided, generate UUID (saved to DB for debugging)
            if seed is None:
                seed = str(uuid.uuid4())
            else:
                # Convert to string if not string
                if not isinstance(seed, str):
                    try:
                        seed = str(seed)
                    except Exception as e:
                        self.logger.error(f"Failed to convert seed to string: {e}")
                        return None
            
            # Calculate hash from seed
            hash_value = self._calculate_hash(seed)
            
            # Check cache
            cache_key = self._get_cache_key(hash_value)
            cached_id = await self.cache_manager.get(cache_key)
            if cached_id is not None:
                return cached_id
            
            # Get master repository
            master_repo = self.database_manager.get_master_repository()
            
            # Use wrapper method to get or create ID
            # seed is always saved to DB (either user-provided or generated UUID) for debugging convenience
            unique_id = await master_repo.get_or_create_id_sequence(
                hash_value=hash_value,
                seed=seed
            )
            
            # Save to cache (if ID obtained)
            if unique_id is not None:
                await self.cache_manager.set(cache_key, unique_id, ttl=self.cache_ttl)
            
            return unique_id
                
        except Exception as e:
            self.logger.error(f"Error generating unique ID: {e}")
            return None
    

