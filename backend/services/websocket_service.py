"""
WebSocket Service

This service provides real-time notifications for scope changes
and other authentication events via WebSocket connections.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from services.scope_manager import ScopeChange
from jose import jwt

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        # Store connections by user_id and tenant_id
        self.connections: Dict[str, Dict[str, Set[WebSocket]]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, token: str) -> bool:
        """
        Accept WebSocket connection and authenticate user
        
        Args:
            websocket: WebSocket connection
            token: JWT authentication token
            
        Returns:
            True if connection successful
        """
        try:
            # Validate token
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            tenant_id = payload.get('tenant_id', '')
            
            if not user_id:
                await websocket.close(code=4001, reason="Invalid token")
                return False
            
            # Accept connection
            await websocket.accept()
            
            # Store connection
            if user_id not in self.connections:
                self.connections[user_id] = {}
            if tenant_id not in self.connections[user_id]:
                self.connections[user_id][tenant_id] = set()
            
            self.connections[user_id][tenant_id].add(websocket)
            
            # Store metadata
            self.connection_metadata[websocket] = {
                'user_id': user_id,
                'tenant_id': tenant_id,
                'connected_at': datetime.utcnow(),
                'last_ping': datetime.utcnow()
            }
            
            logger.info(f"WebSocket connected for user {user_id} in tenant {tenant_id}")
            
            # Send connection confirmation
            await self._send_to_connection(websocket, {
                'type': 'connection_established',
                'user_id': user_id,
                'tenant_id': tenant_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return True
            
        except jwt.InvalidTokenError:
            await websocket.close(code=4001, reason="Invalid token")
            return False
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            await websocket.close(code=4000, reason="Connection error")
            return False
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            user_id = metadata['user_id']
            tenant_id = metadata['tenant_id']
            
            # Remove from connections
            if (user_id in self.connections and 
                tenant_id in self.connections[user_id] and
                websocket in self.connections[user_id][tenant_id]):
                
                self.connections[user_id][tenant_id].remove(websocket)
                
                # Clean up empty sets and dicts
                if not self.connections[user_id][tenant_id]:
                    del self.connections[user_id][tenant_id]
                if not self.connections[user_id]:
                    del self.connections[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(f"WebSocket disconnected for user {user_id} in tenant {tenant_id}")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any], 
                          tenant_id: str = None):
        """
        Send message to all connections for a user
        
        Args:
            user_id: User ID
            message: Message to send
            tenant_id: Specific tenant (None for all tenants)
        """
        if user_id not in self.connections:
            return
        
        if tenant_id is not None:
            # Send to specific tenant
            if tenant_id in self.connections[user_id]:
                await self._send_to_connections(
                    self.connections[user_id][tenant_id], message
                )
        else:
            # Send to all tenants for user
            for tenant_connections in self.connections[user_id].values():
                await self._send_to_connections(tenant_connections, message)
    
    async def send_to_tenant(self, tenant_id: str, message: Dict[str, Any]):
        """
        Send message to all users in a tenant
        
        Args:
            tenant_id: Tenant ID
            message: Message to send
        """
        for user_connections in self.connections.values():
            if tenant_id in user_connections:
                await self._send_to_connections(
                    user_connections[tenant_id], message
                )
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast message to all connected users
        
        Args:
            message: Message to send
        """
        all_connections = set()
        for user_connections in self.connections.values():
            for tenant_connections in user_connections.values():
                all_connections.update(tenant_connections)
        
        await self._send_to_connections(all_connections, message)
    
    async def _send_to_connections(self, connections: Set[WebSocket], 
                                 message: Dict[str, Any]):
        """Send message to multiple connections"""
        if not connections:
            return
        
        # Add timestamp to message
        message['timestamp'] = datetime.utcnow().isoformat()
        message_json = json.dumps(message)
        
        # Send to all connections, remove failed ones
        failed_connections = set()
        
        for websocket in connections:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                failed_connections.add(websocket)
        
        # Clean up failed connections
        for websocket in failed_connections:
            self.disconnect(websocket)
    
    async def _send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to single connection"""
        try:
            message['timestamp'] = datetime.utcnow().isoformat()
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
            self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        count = 0
        for user_connections in self.connections.values():
            for tenant_connections in user_connections.values():
                count += len(tenant_connections)
        return count
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for a specific user"""
        if user_id not in self.connections:
            return 0
        
        count = 0
        for tenant_connections in self.connections[user_id].values():
            count += len(tenant_connections)
        return count
    
    async def ping_connections(self):
        """Send ping to all connections to keep them alive"""
        ping_message = {
            'type': 'ping',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        all_connections = set()
        for user_connections in self.connections.values():
            for tenant_connections in user_connections.values():
                all_connections.update(tenant_connections)
        
        await self._send_to_connections(all_connections, ping_message)

class WebSocketNotificationService:
    """Service for sending real-time notifications via WebSocket"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def notify_scope_change(self, scope_change: ScopeChange):
        """
        Notify user of scope changes
        
        Args:
            scope_change: Scope change event
        """
        message = {
            'type': 'scope_change',
            'user_id': scope_change.user_id,
            'tenant_id': scope_change.tenant_id,
            'old_version': scope_change.old_version,
            'new_version': scope_change.new_version,
            'change_type': scope_change.change_type,
            'changed_capabilities': scope_change.changed_capabilities,
            'changed_roles': scope_change.changed_roles,
            'message': 'Your permissions have been updated. Please refresh your session.'
        }
        
        await self.connection_manager.send_to_user(
            scope_change.user_id, message, scope_change.tenant_id
        )
        
        logger.info(f"Sent scope change notification to user {scope_change.user_id}")
    
    async def notify_session_invalidated(self, user_id: str, tenant_id: str = None,
                                       reason: str = "scope_change"):
        """
        Notify user that their session has been invalidated
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            reason: Reason for invalidation
        """
        message = {
            'type': 'session_invalidated',
            'user_id': user_id,
            'tenant_id': tenant_id,
            'reason': reason,
            'message': 'Your session has been invalidated. Please log in again.'
        }
        
        await self.connection_manager.send_to_user(user_id, message, tenant_id)
        
        logger.info(f"Sent session invalidation notification to user {user_id}")
    
    async def notify_role_change(self, user_id: str, tenant_id: str, 
                               old_role: str, new_role: str):
        """
        Notify user of role changes
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            old_role: Previous role
            new_role: New role
        """
        message = {
            'type': 'role_change',
            'user_id': user_id,
            'tenant_id': tenant_id,
            'old_role': old_role,
            'new_role': new_role,
            'message': f'Your role has been changed from {old_role} to {new_role}.'
        }
        
        await self.connection_manager.send_to_user(user_id, message, tenant_id)
        
        logger.info(f"Sent role change notification to user {user_id}")
    
    async def notify_tenant_access_granted(self, user_id: str, tenant_id: str, 
                                         role: str):
        """
        Notify user of new tenant access
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            role: Assigned role
        """
        message = {
            'type': 'tenant_access_granted',
            'user_id': user_id,
            'tenant_id': tenant_id,
            'role': role,
            'message': f'You have been granted {role} access to tenant {tenant_id}.'
        }
        
        await self.connection_manager.send_to_user(user_id, message)
        
        logger.info(f"Sent tenant access notification to user {user_id}")
    
    async def notify_tenant_access_revoked(self, user_id: str, tenant_id: str):
        """
        Notify user of revoked tenant access
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
        """
        message = {
            'type': 'tenant_access_revoked',
            'user_id': user_id,
            'tenant_id': tenant_id,
            'message': f'Your access to tenant {tenant_id} has been revoked.'
        }
        
        await self.connection_manager.send_to_user(user_id, message, tenant_id)
        
        logger.info(f"Sent tenant access revocation notification to user {user_id}")

# Global instances
connection_manager = None
notification_service = None

def get_connection_manager(secret_key: str) -> ConnectionManager:
    """Get or create connection manager instance"""
    global connection_manager
    if connection_manager is None:
        connection_manager = ConnectionManager(secret_key)
    return connection_manager

def get_notification_service(secret_key: str) -> WebSocketNotificationService:
    """Get or create notification service instance"""
    global notification_service, connection_manager
    if notification_service is None:
        if connection_manager is None:
            connection_manager = ConnectionManager(secret_key)
        notification_service = WebSocketNotificationService(connection_manager)
    return notification_service