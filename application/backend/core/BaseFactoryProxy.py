"""
@Project ：SkyEngine
@File    ：BaseFactoryProxy.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/1/19 14:50
"""

import asyncio
from typing import Optional, Protocol, runtime_checkable
from enum import Enum


class ExecutionStatus(str, Enum):
    """Factory execution status"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@runtime_checkable
class FactoryProxyProtocol(Protocol):
    """
    工厂代理协议 - 定义接口规范（非继承式）

    任何实现了这些方法的类都可以被 server.py 使用，
    无需继承 BaseFactoryProxy。
    """

    # 属性
    inner_properties: dict
    status: ExecutionStatus
    current_step: int

    # 配置方法
    def set_config(self, config: dict) -> None: ...
    def set_algorithm(self, algorithm: str) -> None: ...
    def get_algorithm(self) -> str: ...
    def get_initialized(self) -> Optional[bool]: ...

    # 生命周期方法
    async def initialize(self) -> None: ...
    async def cleanup(self) -> None: ...
    async def start(self) -> None: ...
    async def pause(self) -> None: ...
    async def reset(self) -> None: ...
    async def stop(self) -> None: ...

    # 流式方法
    async def get_state_events(self) -> list: ...
    async def get_metrics_events(self) -> list: ...
    async def get_control_events(self) -> list: ...
    async def get_state_snapshot(self) -> dict: ...
    async def get_metrics_snapshot(self) -> dict: ...
    async def get_control_status(self) -> dict: ...

    # 工具方法
    def is_running(self) -> bool: ...
    def is_paused(self) -> bool: ...
    def is_idle(self) -> bool: ...


class BaseFactoryProxy:
    """
    Base class for factory proxy service layer.

    Provides common interface and shared functionality for all factory proxies.
    Subclasses should implement abstract methods for specific factory types.
    """

    def __init__(self):
        # Execution State
        self.status: ExecutionStatus = ExecutionStatus.IDLE
        self.current_step: int = 0
        self._total_steps: int = 0

        # Data Streaming
        self._state_queue: Optional[asyncio.Queue] = None
        self._metrics_queue: Optional[asyncio.Queue] = None
        self._control_queue: Optional[asyncio.Queue] = None

        # Property
        self.inner_properties: dict = {}  # For storing factory-specific properties

    # ==================== Configuration Methods ====================

    def set_config(self, config: dict):
        """
        Set factory configuration.

        Args:
            config: Factory configuration object or dict
        """
        pass  # To be implemented by subclasses

    def set_algorithm(self, algorithm: str) -> None:
        """
        设置当前工厂的调度算法

        Args:
            algorithm: 算法标识符 (如 'greedy', 'ortools', 'rl' 等)
        """
        if not algorithm:
            return

        # 持久化到 inner_properties
        self.inner_properties["current_algorithm"] = algorithm
        print(f"[BaseFactoryProxy] 调度算法已设置: {algorithm}")

    def get_algorithm(self) -> str:
        """
        获取当前设置的调度算法

        Returns:
            当前算法标识符，未设置时返回默认值 'default'
        """
        return self.inner_properties.get("current_algorithm", "default")

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
