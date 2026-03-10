"""
@Project ：SkyEngine
@File    ：BaseFactoryProxy.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/1/19 14:50
"""

import asyncio
from typing import Optional
from enum import Enum


class ExecutionStatus(str, Enum):
    """Factory execution status"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class BaseFactoryProxy:
    """
    Base class for factory proxy service layer.

    Provides common interface and shared functionality for all factory proxies.
    Subclasses should implement abstract methods for specific factory types.
    """

    def __init__(self):
        # Execution State
        self._status: ExecutionStatus = ExecutionStatus.IDLE
        self._current_step: int = 0
        self._total_steps: int = 0

        # Data Streaming
        self._state_queue: Optional[asyncio.Queue] = None
        self._metrics_queue: Optional[asyncio.Queue] = None
        self._control_queue: Optional[asyncio.Queue] = None

    # ==================== Configuration Methods ====================

    def set_config(self, config: dict):
        """
        Set factory configuration.

        Args:
            config: Factory configuration object or dict
        """
        pass  # To be implemented by subclasses

    async def initialize(self):
        """
        Initialize factory proxy.

        Should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement initialize()")

    async def cleanup(self):
        """
        Cleanup factory resources and stop execution.

        Should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement cleanup()")

    # ==================== Control Methods ====================

    async def start(self):
        """
        Start/resume factory execution.

        Should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement start()")

    async def pause(self):
        """
        Pause factory execution.

        Should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement pause()")

    async def reset(self):
        """
        Reset factory to initial state.

        Should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement reset()")

    async def stop(self):
        """
        Stop factory execution completely.

        Should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement stop()")

    # ==================== Streaming Methods ====================

    async def get_state_events(self) -> list:
        """
        Get state events for SSE stream.
        
        Returns:
            List of tuples: [(event_type, data), ...]
            Default returns single event with type 'state'
        """
        snapshot = await self.get_state_snapshot()
        return [("state", snapshot)]

    async def get_metrics_events(self) -> list:
        """
        Get metrics events for SSE stream.
        
        Returns:
            List of tuples: [(event_type, data), ...]
            Default returns single event with type 'metrics'
        """
        metrics = await self.get_metrics_snapshot()
        return [("metrics", metrics)]

    async def get_control_events(self) -> list:
        """
        Get control events for SSE stream.
        
        Returns:
            List of tuples: [(event_type, data), ...]
            Default returns single event with type 'control'
        """
        status = await self.get_control_status()
        return [("control", status)]

    async def get_state_snapshot(self) -> dict:
        """
        Get current factory state for SSE stream.

        Returns:
            Dictionary containing factory state
        """
        raise NotImplementedError("Subclasses must implement get_state_snapshot()")

    async def get_metrics_snapshot(self) -> dict:
        """
        Get current metrics for SSE stream.

        Returns:
            Dictionary containing factory metrics
        """
        raise NotImplementedError("Subclasses must implement get_metrics_snapshot()")

    async def get_control_status(self) -> dict:
        """
        Get current control status.

        Returns:
            Dictionary containing control status
        """
        raise NotImplementedError("Subclasses must implement get_control_status()")

    # ==================== Utility Methods ====================

    @property
    def status(self) -> ExecutionStatus:
        """Get current execution status"""
        return self._status

    @property
    def current_step(self) -> int:
        """Get current step number"""
        return self._current_step

    def is_running(self) -> bool:
        """Check if factory is running"""
        return self._status == ExecutionStatus.RUNNING

    def is_paused(self) -> bool:
        """Check if factory is paused"""
        return self._status == ExecutionStatus.PAUSED

    def is_idle(self) -> bool:
        """Check if factory is idle"""
        return self._status == ExecutionStatus.IDLE


if __name__ == "__main__":
    # Simple test for BaseFactoryProxy
    print("=== BaseFactoryProxy Test ===")
    print(f"ExecutionStatus values: {[s.value for s in ExecutionStatus]}")

    # Create instance (abstract base class, just testing basic properties)
    proxy = BaseFactoryProxy()
    print(f"Initial status: {proxy.status}")
    print(f"Is idle: {proxy.is_idle()}")
    print(f"Is running: {proxy.is_running()}")
    print(f"Is paused: {proxy.is_paused()}")
    print("BaseFactoryProxy test passed!")
