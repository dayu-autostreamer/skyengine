"""
@Project ：SkyEngine
@File    ：StaticFactoryProxy.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/1/19 14:50
"""

import asyncio
from typing import Optional, Dict, Any
from enum import Enum
import random

# Import base proxy class and ProxyFactory
from .BaseFactoryProxy import BaseFactoryProxy, ExecutionStatus
from .ProxyFactory import ProxyFactory


# ============ 数据库：从 fullSystemTest.js 移植 ============

# AGV 轨迹数据 (0-54 步)
AGV_TRAJECTORIES = [
    {"step": 0, "agvs": [{"x": 5, "y": 2, "active": True}]},
    {"step": 1, "agvs": [{"x": 5, "y": 3, "active": True}]},
    {"step": 2, "agvs": [{"x": 5, "y": 4, "active": True}]},
    {"step": 3, "agvs": [{"x": 5, "y": 5, "active": True}]},
    {"step": 4, "agvs": [{"x": 5, "y": 6, "active": True}]},
    {"step": 5, "agvs": [{"x": 5, "y": 7, "active": True}]},
    {"step": 6, "agvs": [{"x": 5, "y": 8, "active": True}]},
    {"step": 7, "agvs": [{"x": 5, "y": 9, "active": True}]},
    {"step": 8, "agvs": [{"x": 5, "y": 10, "active": True}]},
    {"step": 9, "agvs": [{"x": 5, "y": 11, "active": True}]},
    {"step": 10, "agvs": [{"x": 6, "y": 11, "active": True}]},
    {"step": 11, "agvs": [{"x": 7, "y": 11, "active": True}]},
    {"step": 12, "agvs": [{"x": 8, "y": 11, "active": True}]},
    {"step": 13, "agvs": [{"x": 8, "y": 10, "active": True}]},
    {"step": 14, "agvs": [{"x": 8, "y": 9, "active": True}]},
    {"step": 15, "agvs": [{"x": 8, "y": 8, "active": True}]},
    {"step": 16, "agvs": [{"x": 8, "y": 7, "active": True}]},
    {"step": 17, "agvs": [{"x": 8, "y": 6, "active": True}]},
    {"step": 18, "agvs": [{"x": 8, "y": 5, "active": True}]},
    {"step": 19, "agvs": [{"x": 8, "y": 4, "active": True}]},
    {"step": 20, "agvs": [{"x": 9, "y": 4, "active": True}]},
    {"step": 21, "agvs": [{"x": 10, "y": 4, "active": True}]},
    {"step": 22, "agvs": [{"x": 11, "y": 4, "active": True}]},
    {"step": 23, "agvs": [{"x": 12, "y": 4, "active": True}]},
    {"step": 24, "agvs": [{"x": 13, "y": 4, "active": True}]},
    {"step": 25, "agvs": [{"x": 14, "y": 4, "active": True}]},
    {"step": 26, "agvs": [{"x": 15, "y": 4, "active": True}]},
    {"step": 27, "agvs": [{"x": 16, "y": 4, "active": True}]},
    {"step": 28, "agvs": [{"x": 15, "y": 4, "active": True}]},
    {"step": 29, "agvs": [{"x": 14, "y": 4, "active": True}]},
    {"step": 30, "agvs": [{"x": 14, "y": 5, "active": True}]},
    {"step": 31, "agvs": [{"x": 14, "y": 6, "active": True}]},
    {"step": 32, "agvs": [{"x": 14, "y": 7, "active": True}]},
    {"step": 33, "agvs": [{"x": 14, "y": 8, "active": True}]},
    {"step": 34, "agvs": [{"x": 14, "y": 9, "active": True}]},
    {"step": 35, "agvs": [{"x": 14, "y": 10, "active": True}]},
    {"step": 36, "agvs": [{"x": 14, "y": 11, "active": True}]},
    {"step": 37, "agvs": [{"x": 13, "y": 11, "active": True}]},
    {"step": 38, "agvs": [{"x": 12, "y": 11, "active": True}]},
    {"step": 39, "agvs": [{"x": 11, "y": 11, "active": True}]},
    {"step": 40, "agvs": [{"x": 10, "y": 11, "active": True}]},
    {"step": 41, "agvs": [{"x": 9, "y": 11, "active": True}]},
    {"step": 42, "agvs": [{"x": 8, "y": 11, "active": True}]},
    {"step": 43, "agvs": [{"x": 7, "y": 11, "active": True}]},
    {"step": 44, "agvs": [{"x": 6, "y": 11, "active": True}]},
    {"step": 45, "agvs": [{"x": 5, "y": 11, "active": True}]},
    {"step": 46, "agvs": [{"x": 5, "y": 10, "active": True}]},
    {"step": 47, "agvs": [{"x": 5, "y": 9, "active": True}]},
    {"step": 48, "agvs": [{"x": 5, "y": 8, "active": True}]},
    {"step": 49, "agvs": [{"x": 5, "y": 7, "active": True}]},
    {"step": 50, "agvs": [{"x": 5, "y": 6, "active": True}]},
    {"step": 51, "agvs": [{"x": 5, "y": 5, "active": True}]},
    {"step": 52, "agvs": [{"x": 5, "y": 4, "active": True}]},
    {"step": 53, "agvs": [{"x": 5, "y": 3, "active": True}]},
    {"step": 54, "agvs": [{"x": 5, "y": 2, "active": True}]}
]

# 事件日志
EVENTS_LOG = [
    {"step": 0, "title": "系统就绪", "message": "AGV #1 已上线，坐标 (5, 2)，等待指令", "type": "info"},
    {"step": 10, "title": "进入作业区", "message": "AGV 到达上料缓冲区 (Y=11)，M1 开始预热", "type": "success"},
    {"step": 27, "title": "折返点装载", "message": "AGV 到达最远端 (16, 4)，执行自动装载任务", "type": "task"},
    {"step": 36, "title": "设备告警", "message": "M1 主轴过载 (Load 99%)，触发安全停机", "type": "error"},
    {"step": 43, "title": "故障排除", "message": "M1 重启完成，系统恢复正常运行", "type": "success"},
    {"step": 54, "title": "任务完成", "message": "AGV 返回原点 (5, 2)，作业流程结束", "type": "success"}
]


class FactorySimulator:
    """Factory simulator generating data matching fullSystemTest.js format"""

    @staticmethod
    def generate_machine_states(step: int) -> dict:
        """生成机器状态（匹配前端格式）"""
        # 初始化机器
        m1 = {"id": "M1", "status": "IDLE", "load": 0}
        m2 = {"id": "M2", "status": "IDLE", "load": 0}
        m3 = {"id": "M3", "status": "IDLE", "load": 0}

        # 阶段1: 预热 (Step 5-15)
        if 5 <= step < 16:
            m1 = {"id": "M1", "status": "WORKING", "load": 10 + (step - 5) * 2}

        # 阶段2: 高负荷作业 (Step 16-35)
        if 16 <= step < 36:
            m1 = {"id": "M1", "status": "WORKING", "load": 60 + random.randint(0, 20)}
            m2 = {"id": "M2", "status": "WORKING", "load": 40 + random.randint(0, 10)}

        # 阶段3: 模拟故障 (Step 36-42)
        if 36 <= step <= 42:
            m1 = {"id": "M1", "status": "BROKEN", "load": 99}
            m2 = {"id": "M2", "status": "IDLE", "load": 0}
            m3 = {"id": "M3", "status": "WORKING", "load": 20}

        # 阶段4: 恢复与收尾 (Step 43-54)
        if step > 42:
            cooldown = max(0, 50 - (step - 42) * 5)
            m1 = {"id": "M1", "status": "WORKING", "load": cooldown}
            m2 = {"id": "M2", "status": "WORKING", "load": cooldown // 2}

        # 结束时刻归零
        if step == 54:
            m1 = {"id": "M1", "status": "IDLE", "load": 0}
            m2 = {"id": "M2", "status": "IDLE", "load": 0}

        return {"M1": m1, "M2": m2, "M3": m3}

    @staticmethod
    def get_events(step: int) -> list:
        """获取事件日志"""
        return [event for event in EVENTS_LOG if event["step"] == step]

    @staticmethod
    def generate_metrics_data(step: int) -> dict:
        """生成性能指标数据（匹配前端格式）"""
        # 获取机器状态作为参考
        machines = FactorySimulator.generate_machine_states(step)
        m_load = machines["M1"]["load"]

        # 效率: 随负载升高，故障时下降
        eff_val = 0
        eff_type = "info"

        if 0 < m_load < 80:
            eff_val = 60 + random.random() * 20
            eff_type = "success"
        elif 80 <= m_load < 99:
            eff_val = 90
            eff_type = "warning"
        elif m_load == 99:
            eff_val = 0
            eff_type = "danger"

        # 利用率
        util_val = min(100, step * 2)
        if step > 40:
            util_val = max(0, 100 - (step - 40) * 10)

        return {
            "step": step,
            "machine": {
                "data": [
                    machines["M1"]["load"],
                    machines["M2"]["load"],
                    machines["M3"]["load"],
                    max(0, random.randint(0, 10)),
                    0
                ],
                "labels": ["M1", "M2", "M3", "M4", "M5"]
            },
            "agv": {
                "data": [
                    min(step * 1.5, 100),  # 耗电量
                    2 if 0 < step < 54 else 0,  # 速度
                    step // 10,  # 任务数
                    1 if 36 <= step <= 42 else 0  # 异常
                ]
            },
            "job": {
                "data": [100 + step * 5, step * 2, 0, 0, 0]
            },
            "keyMetrics": {
                "efficiency": {"value": f"{int(eff_val)}%", "type": eff_type},
                "utilization": {"value": f"{int(util_val)}%", "type": "warning" if util_val > 80 else "success"}
            }
        }


@ProxyFactory.register_proxy("static_factory")
@ProxyFactory.register_proxy("northeast_center")
class StaticFactoryProxy(BaseFactoryProxy):
    """
    Static factory proxy that uses mock simulation data.

    Provides the same interface as GridFactoryProxy but uses
    FactorySimulator for mock data generation, matching the
    frontend's expected format.
    """

    def __init__(self):
        # Call parent init
        super().__init__()

        # Execution State
        self._current_step: int = 0
        self._total_steps: int = 55  # Default total steps for mock

    # ==================== Configuration Methods ====================

    def set_config(self, config: dict):
        """Set factory configuration (not used for static proxy)"""
        # Static proxy doesn't need configuration
        pass

    async def initialize(self):
        """Initialize factory proxy"""
        # Initialize queues
        self._state_queue = asyncio.Queue(maxsize=100)
        self._metrics_queue = asyncio.Queue(maxsize=100)
        self._control_queue = asyncio.Queue(maxsize=100)
        self._current_step = 0
        self._status = ExecutionStatus.IDLE

    async def cleanup(self):
        """Cleanup factory resources"""
        # Stop if running
        if self._status == ExecutionStatus.RUNNING:
            await self.stop()

        # Clear queues
        if self._state_queue:
            while not self._state_queue.empty():
                try:
                    self._state_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        self._status = ExecutionStatus.STOPPED

    # ==================== Control Methods ====================

    async def start(self):
        """Start/resume factory execution"""
        if self._status == ExecutionStatus.RUNNING:
            return

        self._status = ExecutionStatus.RUNNING
        # Simple execution loop for testing
        asyncio.create_task(self._run_mock())

    async def _run_mock(self):
        """简单的模拟执行循环，每 1.5 秒一步"""
        while self._status == ExecutionStatus.RUNNING:
            await asyncio.sleep(1.5)  # 匹配前端的 1.5 秒间隔
            
            # 推送状态和指标
            await self._push_state_snapshot()
            await self._push_control_status()
            
            self._current_step += 1
            
            if self._current_step >= self._total_steps:
                await self.stop()
                break

    async def pause(self):
        """Pause factory execution"""
        if self._status == ExecutionStatus.RUNNING:
            self._status = ExecutionStatus.PAUSED

    async def reset(self):
        """Reset factory to initial state"""
        if self._status == ExecutionStatus.RUNNING:
            await self.stop()

        self._current_step = 0
        self._status = ExecutionStatus.IDLE

    async def stop(self):
        """Stop factory execution completely"""
        self._status = ExecutionStatus.STOPPED

    # ==================== Streaming Methods ====================

    async def get_state_events(self) -> list:
        """
        Get state events for SSE stream.
        Returns grid_state event type.
        """
        snapshot = await self.get_state_snapshot()
        return [("grid_state", snapshot)]

    async def get_metrics_events(self) -> list:
        """
        Get metrics events for SSE stream.
        Returns grid_metrics event type.
        """
        metrics = await self.get_metrics_snapshot()
        return [("grid_metrics", metrics)]

    async def get_control_events(self) -> list:
        """
        Get control events for SSE stream.
        Returns command_response event type.
        """
        status = await self.get_control_status()
        return [("command_response", status)]

    async def get_state_snapshot(self) -> dict:
        """
        Get current factory state for SSE stream.
        优先从队列消费数据（保证不跳步），队列空时实时查询兜底

        Returns:
            Dictionary containing factory state (matching frontend format)
        """
        # 策略：优先从队列取（FIFO顺序，不跳步）
        if self._state_queue and not self._state_queue.empty():
            try:
                cached_snapshot = self._state_queue.get_nowait()
                return cached_snapshot
            except asyncio.QueueEmpty:
                pass  # 队列空，fallback到实时查询

        # Fallback：队列空时实时构建快照
        return await self._build_state_snapshot_direct()

    async def _build_state_snapshot_direct(self) -> dict:
        """直接构建状态快照，供_push和fallback使用"""
        # 使用轨迹数据
        step = min(self._current_step, len(AGV_TRAJECTORIES) - 1)
        agv_frame = AGV_TRAJECTORIES[step]
        machine_states = FactorySimulator.generate_machine_states(step)
        events = FactorySimulator.get_events(step)

        # 构建状态快照（匹配前端格式）
        snapshot = {
            "timestamp": f"T+{self._current_step}s",
            "grid_state": {
                "positions_xy": [[agv["x"], agv["y"]] for agv in agv_frame["agvs"]],
                "is_active": [agv["active"] for agv in agv_frame["agvs"]],
            },
            "machines": machine_states,  # 已经是字典格式 {"M1": {...}, "M2": {...}}
            "active_transfers": [],
            "events": events,  # 事件列表
        }

        return snapshot

    async def get_metrics_snapshot(self) -> dict:
        """
        Get current metrics for SSE stream.

        Returns:
            Dictionary containing factory metrics (matching frontend format)
        """
        # 生成指标数据
        metrics = FactorySimulator.generate_metrics_data(self._current_step)
        return metrics

    async def get_control_status(self) -> dict:
        """
        Get current control status.

        Returns:
            Dictionary containing control status
        """
        return {
            "status": self._status.value,
            "current_step": self._current_step,
            "total_steps": self._total_steps,
            "config": {},  # Static proxy doesn't use config
        }

    async def _push_state_snapshot(self):
        """Push state snapshot to queue"""
        if self._state_queue:
            try:
                state = await self._build_state_snapshot_direct()
                if not self._state_queue.full():
                    self._state_queue.put_nowait(state)
                else:
                    # 队列满时，丢弃最旧数据
                    try:
                        self._state_queue.get_nowait()
                        self._state_queue.put_nowait(state)
                    except asyncio.QueueEmpty:
                        pass
            except Exception as e:
                # 静默失败，不影响主流程
                pass

    async def _push_control_status(self):
        """Push control status to queue"""
        if self._control_queue:
            try:
                status = await self.get_control_status()
                if not self._control_queue.full():
                    self._control_queue.put_nowait(status)
            except asyncio.QueueFull:
                # Drop oldest
                try:
                    self._control_queue.get_nowait()
                    self._control_queue.put_nowait(status)
                except asyncio.QueueEmpty:
                    pass

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
    # Simple test for StaticFactoryProxy
    print("=== StaticFactoryProxy Test ===")

    async def test():
        # Create proxy
        proxy = StaticFactoryProxy()
        print(f"Created StaticFactoryProxy, status: {proxy.status}")

        # Initialize
        await proxy.initialize()
        print(f"Initialized, status: {proxy.status}, step: {proxy.current_step}")

        # Get state snapshot
        state = await proxy.get_state_snapshot()
        print(f"State snapshot keys: {list(state.keys())}")
        print(f"Timestamp: {state.get('timestamp')}")

        # Get metrics snapshot
        metrics = await proxy.get_metrics_snapshot()
        print(f"Metrics: {metrics}")

        # Start and run briefly
        await proxy.start()
        print(f"Started, status: {proxy.status}")
        await asyncio.sleep(1.5)  # Run for a bit
        print(f"After 1.5s, step: {proxy.current_step}")

        # Pause
        await proxy.pause()
        print(f"Paused, status: {proxy.status}")

        # Reset
        await proxy.reset()
        print(f"Reset, status: {proxy.status}, step: {proxy.current_step}")

        # Cleanup
        await proxy.cleanup()
        print(f"Cleaned up, status: {proxy.status}")
        print("StaticFactoryProxy test passed!")

    asyncio.run(test())
