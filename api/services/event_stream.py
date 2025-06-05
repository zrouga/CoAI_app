"""
Event streaming service for Server-Sent Events (SSE)
Provides real-time progress updates for pipeline execution
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class EventStreamManager:
    """Manages SSE connections and event broadcasting"""
    
    def __init__(self):
        # Store active connections by keyword
        self._connections: Dict[str, Dict[str, asyncio.Queue]] = defaultdict(dict)
        # Store pipeline state for late joiners
        self._pipeline_state: Dict[str, Dict[str, Any]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def add_connection(self, keyword: str, connection_id: str) -> asyncio.Queue:
        """Add a new SSE connection for a keyword"""
        async with self._lock:
            queue = asyncio.Queue(maxsize=100)
            self._connections[keyword][connection_id] = queue
            
            # Send current state if pipeline already running
            if keyword in self._pipeline_state:
                await queue.put(self._format_event("state_sync", self._pipeline_state[keyword]))
            
            logger.info(f"SSE connection added", extra={"keyword": keyword, "connection_id": connection_id})
            return queue
    
    async def remove_connection(self, keyword: str, connection_id: str):
        """Remove an SSE connection"""
        async with self._lock:
            if keyword in self._connections and connection_id in self._connections[keyword]:
                del self._connections[keyword][connection_id]
                if not self._connections[keyword]:
                    del self._connections[keyword]
                logger.info(f"SSE connection removed", extra={"keyword": keyword, "connection_id": connection_id})
    
    async def broadcast_event(self, keyword: str, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all connections watching this keyword"""
        async with self._lock:
            # Update pipeline state
            if event_type == "pipeline_start":
                self._pipeline_state[keyword] = {
                    "status": "running",
                    "started_at": datetime.now().isoformat(),
                    "current_step": "step1",
                    "events": []
                }
            elif keyword in self._pipeline_state:
                self._pipeline_state[keyword]["events"].append({
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
                
                if event_type == "pipeline_complete":
                    self._pipeline_state[keyword]["status"] = "completed"
                elif event_type == "pipeline_error":
                    self._pipeline_state[keyword]["status"] = "failed"
            
            # Broadcast to all connections
            if keyword in self._connections:
                event = self._format_event(event_type, data)
                dead_connections = []
                
                for conn_id, queue in self._connections[keyword].items():
                    try:
                        # Non-blocking put with timeout
                        await asyncio.wait_for(queue.put(event), timeout=1.0)
                    except (asyncio.QueueFull, asyncio.TimeoutError):
                        # Mark connection for removal if queue is full
                        dead_connections.append(conn_id)
                        logger.warning(f"SSE queue full, dropping connection", 
                                     extra={"keyword": keyword, "connection_id": conn_id})
                
                # Clean up dead connections
                for conn_id in dead_connections:
                    del self._connections[keyword][conn_id]
    
    def _format_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format data as SSE event"""
        event_data = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        return f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
    
    async def clear_pipeline_state(self, keyword: str):
        """Clear pipeline state after completion"""
        async with self._lock:
            if keyword in self._pipeline_state:
                del self._pipeline_state[keyword]

# Global event stream manager instance
event_manager = EventStreamManager()

class PipelineEventEmitter:
    """Helper class to emit pipeline progress events"""
    
    def __init__(self, keyword: str, correlation_id: Optional[str] = None):
        self.keyword = keyword
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.start_time = datetime.now()
    
    async def emit_start(self, config: Dict[str, Any]):
        """Emit pipeline start event"""
        await event_manager.broadcast_event(
            self.keyword,
            "pipeline_start",
            {
                "correlation_id": self.correlation_id,
                "config": config,
                "message": f"Starting pipeline for keyword: {self.keyword}"
            }
        )
    
    async def emit_step_start(self, step: int, step_name: str, details: str):
        """Emit step start event"""
        await event_manager.broadcast_event(
            self.keyword,
            f"step{step}_start",
            {
                "correlation_id": self.correlation_id,
                "step": step,
                "step_name": step_name,
                "details": details,
                "message": f"Step {step} started: {step_name}"
            }
        )
    
    async def emit_step_progress(self, step: int, progress: int, total: int, current_item: str = None):
        """Emit step progress event"""
        await event_manager.broadcast_event(
            self.keyword,
            f"step{step}_progress",
            {
                "correlation_id": self.correlation_id,
                "step": step,
                "progress": progress,
                "total": total,
                "percentage": round((progress / total * 100) if total > 0 else 0, 1),
                "current_item": current_item,
                "message": f"Step {step}: {progress}/{total} completed"
            }
        )
    
    async def emit_step_complete(self, step: int, results: Dict[str, Any]):
        """Emit step completion event"""
        duration = (datetime.now() - self.start_time).total_seconds()
        await event_manager.broadcast_event(
            self.keyword,
            f"step{step}_complete",
            {
                "correlation_id": self.correlation_id,
                "step": step,
                "results": results,
                "duration_seconds": round(duration, 1),
                "message": f"Step {step} completed successfully"
            }
        )
    
    async def emit_pipeline_complete(self, summary: Dict[str, Any]):
        """Emit pipeline completion event"""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        await event_manager.broadcast_event(
            self.keyword,
            "pipeline_complete",
            {
                "correlation_id": self.correlation_id,
                "summary": summary,
                "total_duration_seconds": round(total_duration, 1),
                "message": "Pipeline completed successfully"
            }
        )
    
    async def emit_error(self, error: str, step: Optional[int] = None):
        """Emit error event"""
        await event_manager.broadcast_event(
            self.keyword,
            "pipeline_error",
            {
                "correlation_id": self.correlation_id,
                "error": error,
                "step": step,
                "message": f"Pipeline error: {error}"
            }
        )
    
    async def emit_log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Emit log event for real-time log streaming"""
        await event_manager.broadcast_event(
            self.keyword,
            "log",
            {
                "correlation_id": self.correlation_id,
                "level": level,
                "message": message,
                "extra": extra or {},
                "timestamp": datetime.now().isoformat()
            }
        ) 