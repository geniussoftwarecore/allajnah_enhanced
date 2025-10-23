import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import redis
from flask import request

class SessionService:
    """Service for managing user sessions with Redis"""
    
    def __init__(self):
        redis_url = os.environ.get('REDIS_URL', '')
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_available = True
            except Exception as e:
                print(f"Redis connection failed: {e}. Using in-memory fallback.")
                self.redis_client = None
                self.redis_available = False
                self.memory_store = {}
        else:
            self.redis_client = None
            self.redis_available = False
            self.memory_store = {}
    
    def _get_session_key(self, refresh_token: str) -> str:
        """Generate Redis key for a session"""
        return f"session:{refresh_token}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        """Generate Redis key for user's session list"""
        return f"user_sessions:{user_id}"
    
    def _get_device_info(self) -> str:
        """Extract device information from request"""
        try:
            user_agent = request.headers.get('User-Agent', 'Unknown')
            if 'Mobile' in user_agent:
                return 'Mobile Device'
            elif 'Tablet' in user_agent:
                return 'Tablet'
            else:
                return 'Desktop/Laptop'
        except RuntimeError:
            return 'Unknown'
    
    def _get_ip_address(self) -> str:
        """Get client IP address"""
        try:
            if request.headers.get('X-Forwarded-For'):
                return request.headers.get('X-Forwarded-For').split(',')[0].strip()
            return request.remote_addr or 'Unknown'
        except RuntimeError:
            return 'Unknown'
    
    def create_session(
        self, 
        user_id: str, 
        device_info: Optional[str] = None,
        expires_days: int = 30
    ) -> str:
        """
        Create a new session and return refresh token.
        
        Args:
            user_id: User ID
            device_info: Optional device information
            expires_days: Session expiration in days (default: 30)
            
        Returns:
            Refresh token string
        """
        refresh_token = str(uuid.uuid4())
        
        if device_info is None:
            device_info = self._get_device_info()
        
        session_data = {
            'user_id': user_id,
            'device': device_info,
            'ip_address': self._get_ip_address(),
            'created_at': datetime.utcnow().isoformat(),
            'last_used': datetime.utcnow().isoformat()
        }
        
        expires_seconds = expires_days * 24 * 60 * 60
        
        if self.redis_available and self.redis_client:
            try:
                session_key = self._get_session_key(refresh_token)
                user_sessions_key = self._get_user_sessions_key(user_id)
                
                self.redis_client.setex(
                    session_key,
                    expires_seconds,
                    json.dumps(session_data)
                )
                
                self.redis_client.sadd(user_sessions_key, refresh_token)
                self.redis_client.expire(user_sessions_key, expires_seconds)
                
            except Exception as e:
                print(f"Redis session creation failed: {e}")
                self.memory_store[refresh_token] = session_data
        else:
            self.memory_store[refresh_token] = session_data
        
        return refresh_token
    
    def validate_session(self, refresh_token: str) -> Optional[Dict]:
        """
        Validate a session and return session data.
        
        Args:
            refresh_token: Refresh token to validate
            
        Returns:
            Session data dict if valid, None otherwise
        """
        if not refresh_token:
            return None
        
        if self.redis_available and self.redis_client:
            try:
                session_key = self._get_session_key(refresh_token)
                session_json = self.redis_client.get(session_key)
                
                if session_json:
                    session_data = json.loads(session_json)
                    session_data['last_used'] = datetime.utcnow().isoformat()
                    
                    ttl = self.redis_client.ttl(session_key)
                    self.redis_client.setex(
                        session_key,
                        ttl if ttl > 0 else 3600,
                        json.dumps(session_data)
                    )
                    
                    return session_data
                return None
                
            except Exception as e:
                print(f"Redis session validation failed: {e}")
                return self.memory_store.get(refresh_token)
        else:
            return self.memory_store.get(refresh_token)
    
    def revoke_session(self, refresh_token: str) -> bool:
        """
        Revoke a session.
        
        Args:
            refresh_token: Refresh token to revoke
            
        Returns:
            True if session was revoked, False otherwise
        """
        if not refresh_token:
            return False
        
        if self.redis_available and self.redis_client:
            try:
                session_key = self._get_session_key(refresh_token)
                session_json = self.redis_client.get(session_key)
                
                if session_json:
                    session_data = json.loads(session_json)
                    user_id = session_data.get('user_id')
                    
                    if user_id:
                        user_sessions_key = self._get_user_sessions_key(user_id)
                        self.redis_client.srem(user_sessions_key, refresh_token)
                    
                    self.redis_client.delete(session_key)
                    return True
                return False
                
            except Exception as e:
                print(f"Redis session revocation failed: {e}")
                if refresh_token in self.memory_store:
                    del self.memory_store[refresh_token]
                    return True
                return False
        else:
            if refresh_token in self.memory_store:
                del self.memory_store[refresh_token]
                return True
            return False
    
    def revoke_all_user_sessions(self, user_id: str) -> int:
        """
        Revoke all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions revoked
        """
        if not user_id:
            return 0
        
        count = 0
        
        if self.redis_available and self.redis_client:
            try:
                user_sessions_key = self._get_user_sessions_key(user_id)
                refresh_tokens = self.redis_client.smembers(user_sessions_key)
                
                for token in refresh_tokens:
                    session_key = self._get_session_key(token)
                    self.redis_client.delete(session_key)
                    count += 1
                
                self.redis_client.delete(user_sessions_key)
                
            except Exception as e:
                print(f"Redis bulk session revocation failed: {e}")
                tokens_to_delete = [
                    token for token, data in self.memory_store.items()
                    if data.get('user_id') == user_id
                ]
                for token in tokens_to_delete:
                    del self.memory_store[token]
                    count += 1
        else:
            tokens_to_delete = [
                token for token, data in self.memory_store.items()
                if data.get('user_id') == user_id
            ]
            for token in tokens_to_delete:
                del self.memory_store[token]
                count += 1
        
        return count
    
    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of session data dictionaries
        """
        if not user_id:
            return []
        
        sessions = []
        
        if self.redis_available and self.redis_client:
            try:
                user_sessions_key = self._get_user_sessions_key(user_id)
                refresh_tokens = self.redis_client.smembers(user_sessions_key)
                
                for token in refresh_tokens:
                    session_key = self._get_session_key(token)
                    session_json = self.redis_client.get(session_key)
                    
                    if session_json:
                        session_data = json.loads(session_json)
                        session_data['refresh_token'] = token
                        sessions.append(session_data)
                
            except Exception as e:
                print(f"Redis get user sessions failed: {e}")
                sessions = [
                    {**data, 'refresh_token': token}
                    for token, data in self.memory_store.items()
                    if data.get('user_id') == user_id
                ]
        else:
            sessions = [
                {**data, 'refresh_token': token}
                for token, data in self.memory_store.items()
                if data.get('user_id') == user_id
            ]
        
        sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return sessions

session_service = SessionService()
