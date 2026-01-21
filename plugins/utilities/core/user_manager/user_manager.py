"""
Utility for managing user data with caching
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class UserManager:
    """
    Utility for managing user data with caching
    - Automatic user data saving
    - Caching to prevent frequent DB access
    - API for working with user data
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.database_manager = kwargs['database_manager']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.cache_manager = kwargs['cache_manager']
        
        # Get settings through settings_manager
        settings = self.settings_manager.get_plugin_settings("user_manager")
        
        # TTL for cache (used when explicitly specified, otherwise taken from cache_manager)
        self.cache_ttl = settings.get('cache_ttl', 600)  # 10 minutes by default
        
        # Get master repository
        self._master_repository = None
    
    def _get_master_repository(self):
        """Get master repository (lazy initialization)"""
        if self._master_repository is None:
            self._master_repository = self.database_manager.get_master_repository()
        return self._master_repository
    
    def _get_cache_key(self, user_id: int, tenant_id: int) -> str:
        """Generate cache key in cache_manager format"""
        return f"user:{user_id}:{tenant_id}"
    
    async def save_user_data(self, user_data: Dict[str, Any]) -> bool:
        """
        Save user data with caching
        """
        try:
            user_id = user_data.get('user_id')
            tenant_id = user_data.get('tenant_id')
            
            if not user_id or not tenant_id:
                self.logger.warning("[UserManager] user_id and tenant_id are required for saving user data")
                return False
            
            cache_key = self._get_cache_key(user_id, tenant_id)
            
            # Check cache through cache_manager
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data is not None:
                # Data exists in cache - do nothing
                return True
            
            # Get master repository
            master_repo = self._get_master_repository()
            
            # Check if user exists
            existing_user = await master_repo.get_user_by_id(user_id, tenant_id)
            
            if existing_user is not None:
                # Update existing user
                success = await master_repo.update_user(user_id, tenant_id, user_data)
                if not success:
                    self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Error updating user")
                    return False
            else:
                # Create new user
                success = await master_repo.create_user(user_data)
                if not success:
                    self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Error creating user")
                    return False
            
            # Load full data from DB after operation
            full_user_data = await master_repo.get_user_by_id(user_id, tenant_id)
            
            # Save full data to cache through cache_manager
            await self.cache_manager.set(cache_key, full_user_data.copy(), ttl=self.cache_ttl)
            
            return True
                
        except Exception as e:
            self.logger.error(f"Error in save_user_data: {e}")
            return False
    
    async def get_user_by_id(self, user_id: int, tenant_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get user data
        """
        try:
            cache_key = self._get_cache_key(user_id, tenant_id)
            
            # Check cache through cache_manager (if not forced refresh)
            if not force_refresh:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data is not None:
                    return cached_data.copy()
            
            # Get from DB
            master_repo = self._get_master_repository()
            user_data = await master_repo.get_user_by_id(user_id, tenant_id)
            
            if user_data:
                # Save to cache through cache_manager
                await self.cache_manager.set(cache_key, user_data.copy(), ttl=self.cache_ttl)
                
                return user_data
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error in get_user_data: {e}")
            return None
    
    async def set_user_state(self, user_id: int, tenant_id: int, state: Optional[str], expires_in_seconds: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Set user state with return of full user data
        """
        try:
            # If state is None or empty string - reset
            if state is None or state == "":
                success = await self.clear_user_state(user_id, tenant_id)
                if success:
                    return await self.get_user_by_id(user_id, tenant_id, force_refresh=True)
                else:
                    return None
            
            # Calculate expiration time
            if expires_in_seconds is None or expires_in_seconds == 0:
                # Forever - set date to year 3000
                expires_at = datetime(3000, 1, 1, 0, 0, 0)
            else:
                # Add seconds to current time
                current_time = await self.datetime_formatter.now_local()
                expires_at = current_time + timedelta(seconds=expires_in_seconds)
            
            # Update DB
            master_repo = self._get_master_repository()
            success = await master_repo.update_user(user_id, tenant_id, {
                'user_state': state,
                'user_state_expired_at': expires_at
            })
            
            if success:
                # Get updated data (forced)
                return await self.get_user_by_id(user_id, tenant_id, force_refresh=True)
            else:
                self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Error setting state")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in set_user_state: {e}")
            return None
    
    async def _validate_user_state(self, user_id: int, tenant_id: int, state: Optional[str], expires_at: Optional[datetime]) -> Optional[str]:
        """
        Validate user state with expiration check
        """
        # Check expiration
        if state is not None and expires_at is None:
            # Error - has state but no expiration date, clear state
            self.logger.warning(f"[Tenant-{tenant_id}] [User-{user_id}] State without expiration date - clearing")
            await self.clear_user_state(user_id, tenant_id)
            return None
        elif expires_at is not None and await self.datetime_formatter.now_local() > expires_at:
            # State expired - clear
            await self.clear_user_state(user_id, tenant_id)
            return None
        
        return state

    async def get_user_state(self, user_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user state with expiration check
        Returns dictionary with state and expiration time
        """
        try:
            # Get user data (method works with cache itself)
            user_data = await self.get_user_by_id(user_id, tenant_id)
            
            if user_data:
                state = user_data.get('user_state')
                expires_at = user_data.get('user_state_expired_at')
                
                # Check expiration
                validated_state = await self._validate_user_state(user_id, tenant_id, state, expires_at)
                
                return {
                    'user_state': validated_state,
                    'user_state_expired_at': expires_at if validated_state else None
                }
            else:
                return {
                    'user_state': None,
                    'user_state_expired_at': None
                }
                
        except Exception as e:
            self.logger.error(f"Error in get_user_state: {e}")
            return None
    
    async def clear_user_state(self, user_id: int, tenant_id: int) -> bool:
        """
        Clear user state
        """
        try:
            # Update DB
            master_repo = self._get_master_repository()
            success = await master_repo.update_user(user_id, tenant_id, {
                'user_state': None,
                'user_state_expired_at': None
            })
            
            if success:
                # Clear cache for this user through cache_manager
                cache_key = self._get_cache_key(user_id, tenant_id)
                await self.cache_manager.delete(cache_key)
                return True
            else:
                self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Error clearing state")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in clear_user_state: {e}")
            return False
