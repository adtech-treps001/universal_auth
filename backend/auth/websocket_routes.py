"""
WebSocket Routes

This module provides WebSocket endpoints for real-time notifications
and scope change updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from services.websocket_service import get_connection_manager, get_notification_service
from services.scope_manager import get_scope_manager
from sqlalchemy.orm import Session
from database import get_db
import asyncio
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration - should be injected from app config
SECRET_KEY = "your-secret-key-here"  # This should come from environment

@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications
    
    Query Parameters:
        token: JWT authentication token
    
    Message Types Sent:
        - connection_established: Confirmation of successful connection
        - scope_change: User scope/permissions have changed
        - session_invalidated: User session has been invalidated
        - role_change: User role has been changed
        - tenant_access_granted: User granted access to new tenant
        - tenant_access_revoked: User access to tenant revoked
        - ping: Keep-alive ping
    """
    connection_manager = get_connection_manager(SECRET_KEY)
    
    # Attempt to connect
    connected = await connection_manager.connect(websocket, token)
    if not connected:
        return
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for incoming message with timeout
                message = await asyncio.wait_for(
                    websocket.receive_text(), 
                    timeout=30.0
                )
                
                # Parse and handle message
                await handle_websocket_message(websocket, message, db)
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await connection_manager._send_to_connection(websocket, {
                    'type': 'ping'
                })
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        connection_manager.disconnect(websocket)

async def handle_websocket_message(websocket: WebSocket, message: str, db: Session):
    """
    Handle incoming WebSocket messages
    
    Args:
        websocket: WebSocket connection
        message: Raw message string
        db: Database session
    """
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        if message_type == 'pong':
            # Handle pong response
            await handle_pong(websocket, data)
        elif message_type == 'scope_check':
            # Handle scope version check request
            await handle_scope_check(websocket, data, db)
        elif message_type == 'subscribe':
            # Handle subscription to specific events
            await handle_subscribe(websocket, data)
        else:
            logger.warning(f"Unknown WebSocket message type: {message_type}")
    
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in WebSocket message")
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")

async def handle_pong(websocket: WebSocket, data: dict):
    """Handle pong response from client"""
    connection_manager = get_connection_manager(SECRET_KEY)
    
    # Update last ping time in metadata
    if websocket in connection_manager.connection_metadata:
        from datetime import datetime
        connection_manager.connection_metadata[websocket]['last_ping'] = datetime.utcnow()

async def handle_scope_check(websocket: WebSocket, data: dict, db: Session):
    """
    Handle scope version check request
    
    Args:
        websocket: WebSocket connection
        data: Message data
        db: Database session
    """
    connection_manager = get_connection_manager(SECRET_KEY)
    
    if websocket not in connection_manager.connection_metadata:
        return
    
    metadata = connection_manager.connection_metadata[websocket]
    user_id = metadata['user_id']
    tenant_id = metadata['tenant_id']
    
    # Get current scope version
    scope_manager = get_scope_manager(db)
    current_version = scope_manager.get_user_scope_version(user_id, tenant_id)
    
    # Send scope version response
    response = {
        'type': 'scope_check_response',
        'user_id': user_id,
        'tenant_id': tenant_id,
        'current_scope_version': current_version,
        'request_id': data.get('request_id')
    }
    
    await connection_manager._send_to_connection(websocket, response)

async def handle_subscribe(websocket: WebSocket, data: dict):
    """
    Handle subscription to specific event types
    
    Args:
        websocket: WebSocket connection
        data: Message data with subscription preferences
    """
    connection_manager = get_connection_manager(SECRET_KEY)
    
    if websocket not in connection_manager.connection_metadata:
        return
    
    # Store subscription preferences in metadata
    event_types = data.get('event_types', [])
    connection_manager.connection_metadata[websocket]['subscriptions'] = event_types
    
    # Send subscription confirmation
    response = {
        'type': 'subscription_confirmed',
        'subscribed_events': event_types,
        'request_id': data.get('request_id')
    }
    
    await connection_manager._send_to_connection(websocket, response)

@router.get("/ws/stats")
async def websocket_stats():
    """
    Get WebSocket connection statistics
    
    Returns:
        Connection statistics
    """
    connection_manager = get_connection_manager(SECRET_KEY)
    
    return {
        'total_connections': connection_manager.get_connection_count(),
        'users_connected': len(connection_manager.connections),
        'connection_details': {
            user_id: {
                tenant_id: len(connections)
                for tenant_id, connections in user_connections.items()
            }
            for user_id, user_connections in connection_manager.connections.items()
        }
    }

@router.post("/ws/broadcast")
async def broadcast_message(
    message: dict,
    db: Session = Depends(get_db)
):
    """
    Broadcast message to all connected users (admin only)
    
    Args:
        message: Message to broadcast
    
    Note: This endpoint should be protected with admin authentication
    """
    connection_manager = get_connection_manager(SECRET_KEY)
    
    # Add broadcast metadata
    broadcast_message = {
        'type': 'broadcast',
        'content': message,
        'sender': 'system'
    }
    
    await connection_manager.broadcast(broadcast_message)
    
    return {
        'success': True,
        'message': 'Message broadcasted',
        'recipients': connection_manager.get_connection_count()
    }

@router.post("/ws/notify-user/{user_id}")
async def notify_user(
    user_id: str,
    message: dict,
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Send notification to specific user (admin only)
    
    Args:
        user_id: Target user ID
        message: Message to send
        tenant_id: Optional tenant context
    
    Note: This endpoint should be protected with admin authentication
    """
    connection_manager = get_connection_manager(SECRET_KEY)
    
    # Add notification metadata
    notification_message = {
        'type': 'admin_notification',
        'content': message,
        'sender': 'admin'
    }
    
    await connection_manager.send_to_user(user_id, notification_message, tenant_id)
    
    user_connections = connection_manager.get_user_connection_count(user_id)
    
    return {
        'success': True,
        'message': f'Notification sent to user {user_id}',
        'user_connections': user_connections
    }

# Background task to keep connections alive
async def websocket_keepalive_task():
    """Background task to send periodic pings to keep connections alive"""
    connection_manager = get_connection_manager(SECRET_KEY)
    
    while True:
        try:
            await connection_manager.ping_connections()
            await asyncio.sleep(30)  # Ping every 30 seconds
        except Exception as e:
            logger.error(f"Error in WebSocket keepalive task: {e}")
            await asyncio.sleep(30)

# Function to start background tasks
def start_websocket_background_tasks():
    """Start WebSocket background tasks"""
    asyncio.create_task(websocket_keepalive_task())
    logger.info("Started WebSocket background tasks")