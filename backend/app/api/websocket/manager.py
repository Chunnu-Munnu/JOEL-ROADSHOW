from fastapi import WebSocket
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manage WebSocket connections for multiple cameras and clients"""
    
    def __init__(self):
        # {camera_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
        # {websocket: camera_id}
        self.connection_map: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, camera_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        if camera_id not in self.active_connections:
            self.active_connections[camera_id] = []
        
        self.active_connections[camera_id].append(websocket)
        self.connection_map[websocket] = camera_id
        
        logger.info(f"Client connected to camera {camera_id}. Total connections: {len(self.active_connections[camera_id])}")
    
    def disconnect(self, websocket: WebSocket, camera_id: str):
        """Remove WebSocket connection"""
        if camera_id in self.active_connections:
            self.active_connections[camera_id].remove(websocket)
            
            if len(self.active_connections[camera_id]) == 0:
                del self.active_connections[camera_id]
        
        if websocket in self.connection_map:
            del self.connection_map[websocket]
        
        logger.info(f"Client disconnected from camera {camera_id}")
    
    async def broadcast_to_camera(self, camera_id: str, message: dict):
        """Broadcast message to all clients watching a specific camera"""
        if camera_id not in self.active_connections:
            return
        
        disconnected = []
        for websocket in self.active_connections[camera_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, camera_id)
    
    async def broadcast_alert(self, alert: dict):
        """Broadcast alert to all connected clients"""
        for camera_id, connections in self.active_connections.items():
            for websocket in connections:
                try:
                    await websocket.send_json({
                        "type": "alert",
                        "data": alert
                    })
                except Exception as e:
                    logger.error(f"Failed to broadcast alert: {e}")
    
    def get_active_cameras(self) -> List[str]:
        """Get list of cameras with active connections"""
        return list(self.active_connections.keys())
    
    def get_connection_count(self, camera_id: str = None) -> int:
        """Get number of active connections"""
        if camera_id:
            return len(self.active_connections.get(camera_id, []))
        return sum(len(conns) for conns in self.active_connections.values())