# Developer Quick Start Guide

This guide is for developers who want to extend the SkyEngine platform, including testing, adding new factory environments, frontend-backend integration, and creating new factory proxies.

## Table of Contents

1. [Project Architecture Overview](#1-project-architecture-overview)
2. [Development Environment Setup](#2-development-environment-setup)
3. [Testing](#3-testing)
4. [Adding New Factory Environments](#4-adding-new-factory-environments)
5. [Creating New Factory Proxies](#5-creating-new-factory-proxies)
6. [Frontend-Backend Integration](#6-frontend-backend-integration)
7. [Debugging & Troubleshooting](#7-debugging--troubleshooting)

---

## 1. Project Architecture Overview

SkyEngine follows a **two-layer decoupled architecture**:

```
+---------------------------------------------------------+
|                 Service Layer (application/)            |
|  +-----------------+  +-----------------------------+   |
|  |  FastAPI Server |  |  Vue.js Frontend            |   |
|  |  (port 8000)    |  |  + ECharts Visualization    |   |
|  +--------+--------+  +-----------------------------+   |
|           |                     ^                        |
|           v                     |                        |
|  +---------------------------------------------+         |
|  |              FactoryProxy Layer             |         |
|  |  BaseFactoryProxy -> GridFactoryProxy, etc.|         |
|  +---------------------------------------------+         |
+---------------------------------------------------------+
                          |
                          v
+---------------------------------------------------------+
|              Algorithm Layer (sky_executor/)            |
|  +---------------------------------------------+         |
|  |  factory_template/ (Abstract Interfaces)    |         |
|  |  - BaseFactory, BaseEnvironment, Status     |         |
|  +---------------------------------------------+         |
|  +---------------------------------------------+         |
|  |  Pluggable Components                       |         |
|  |  - JobSolver, Assigner, RouteSolver         |         |
|  +---------------------------------------------+         |
+---------------------------------------------------------+
```

**Key Principle**: The service layer contains no scheduling logic; the algorithm layer has no business interface dependencies.

---

## 2. Development Environment Setup

### 2.1 Backend Setup

```bash
# Navigate to project root
cd SkyEngine

# Install dependencies using uv
uv sync

# Start the backend server
uv run uvicorn application.backend.server:app --reload --port 8000
```

### 2.2 Frontend Setup

```bash
# Navigate to frontend directory
cd application/frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### 2.3 Verify Installation

1. Backend health check: `curl http://localhost:8000/health`
2. Frontend: Open `http://localhost:5173` (or the port shown)
3. First time enter please using Northeastern center only for test

---

## 3. Testing

### 3.1 Frontend Scenario Testing

The project includes a built-in scenario test system located at `application/frontend/src/scenarios/fullSystemTest.js`.

**Running the Test:**

```javascript
import { runFullSystemTest } from '@/scenarios/fullSystemTest.js';

// In your Vue component
const stopTest = runFullSystemTest(store, monitorStore, () => {
  console.log('Test completed');
  isRunningTest.value = false;
});

// To stop the test
stopTest?.();
```

**Test Data Structure:**

```javascript
// AGV trajectories (55 steps)
const AGV_TRAJECTORIES = [
  { step: 0, agvs: [{ x: 5, y: 2, active: true }, ...] },
  // ...
];

// Machine states
const MACHINE_STATES = [...];

// Performance metrics
const METRICS_DATA = [...];

// Event logs
const EVENTS_LOG = [...];
```

### 3.2 Static Factory Proxy Testing

Use `StaticFactoryProxy` for offline testing and algorithm validation:

```python
from application.backend.core.ProxyFactory import ProxyFactory

# Create static proxy
proxy = ProxyFactory.create("static_factory")
# or
proxy = ProxyFactory.create("northeast_center")  # alias

await proxy.initialize()
await proxy.start()

# Get state snapshots
state = await proxy.get_state_snapshot()
```

### 3.3 Adding New Tests

Create a new test file in `application/frontend/src/scenarios/`:

```javascript
// myScenario.js
export function runMyScenario(store, monitorStore, onComplete) {
  const testData = [
    { timestamp: "T+0", grid_state: {...}, machines: {...} },
    { timestamp: "T+1", grid_state: {...}, machines: {...} },
  ];

  let stepIndex = 0;

  function pushNextFrame() {
    if (stepIndex >= testData.length) {
      onComplete?.();
      return;
    }

    store.pushSnapshot(testData[stepIndex]);
    stepIndex++;
    setTimeout(pushNextFrame, 1000);
  }

  pushNextFrame();

  return () => {
    // Cleanup function
    stepIndex = testData.length;
  };
}
```

### 3.4 Recommended Test Structure

```
tests/
|-- unit/
|   |-- test_proxy_factory.py
|   |-- test_base_proxy.py
|   |-- test_sse_manager.py
|-- integration/
|   |-- test_frontend_backend.py
|   |-- test_factory_switching.py
|-- e2e/
    |-- test_full_workflow.py
```

---

## 4. Adding New Factory Environments

### 4.1 Environment Interface

All factory environments should implement the `BaseEnvironment` interface:

```python
# sky_executor/factory_template/factory_core/base_environment.py

from abc import ABC, abstractmethod
from typing import Any, Tuple, Dict

class BaseEnvironment(ABC):
    """Abstract environment interface (Gymnasium-like)"""

    @abstractmethod
    def reset(self, seed: int = None) -> Tuple[Dict, Dict]:
        """
        Reset environment to initial state.
        Returns: Tuple[observation, info]
        """
        pass

    @abstractmethod
    def step(self, action: Any) -> Tuple[Dict, float, bool, bool, Dict]:
        """
        Execute one step.
        Returns: Tuple[observation, reward, terminated, truncated, info]
        """
        pass

    @abstractmethod
    def get_state(self) -> Dict:
        """Get current environment state."""
        pass

    @abstractmethod
    def set_state(self, state: Dict) -> None:
        """Set environment state."""
        pass

    @abstractmethod
    def render(self) -> Any:
        """Render current state (optional)."""
        pass
```

### 4.2 Creating a New Environment

**Step 1: Create the Environment Class**

```python
# sky_executor/my_factory/my_environment.py

from sky_executor.factory_template.factory_core.base_environment import BaseEnvironment
from dataclasses import dataclass
from typing import Dict, Tuple, Any

@dataclass
class MyEnvironmentConfig:
    grid_size: int = 10
    num_agents: int = 4
    max_steps: int = 100

class MyEnvironment(BaseEnvironment):
    def __init__(self, config: MyEnvironmentConfig = None):
        self.config = config or MyEnvironmentConfig()
        self.current_step = 0
        self.state = {}

    def reset(self, seed: int = None) -> Tuple[Dict, Dict]:
        """Reset to initial state"""
        self.current_step = 0
        self.state = {
            "positions": [[0, 0] for _ in range(self.config.num_agents)],
            "step": 0
        }
        return self.state, {"info": "reset"}

    def step(self, action: Any) -> Tuple[Dict, float, bool, bool, Dict]:
        """Execute one step"""
        # Apply action logic here
        self.current_step += 1
        done = self.current_step >= self.config.max_steps
        reward = 1.0 if not done else 0.0
        return self.state, reward, done, False, {}

    def get_state(self) -> Dict:
        return self.state.copy()

    def set_state(self, state: Dict) -> None:
        self.state = state.copy()

    def render(self) -> Any:
        return self.state
```

**Step 2: Create the Factory Manager**

```python
# sky_executor/my_factory/my_factory.py

from sky_executor.factory_template.factory_core.base_factory import BaseFactory
from sky_executor.factory_template.factory_core.execution_status import ExecutionStatus
from .my_environment import MyEnvironment, MyEnvironmentConfig

class MyFactory(BaseFactory):
    def __init__(self, config: MyEnvironmentConfig = None):
        self.config = config or MyEnvironmentConfig()
        self.env = MyEnvironment(self.config)
        self.status = ExecutionStatus.IDLE
        self.current_step = 0

    def initialize(self) -> None:
        self.env.reset()
        self.status = ExecutionStatus.IDLE
        self.current_step = 0

    def start(self) -> None:
        self.status = ExecutionStatus.RUNNING

    def pause(self) -> None:
        self.status = ExecutionStatus.PAUSED

    def reset(self) -> None:
        self.env.reset()
        self.current_step = 0
        self.status = ExecutionStatus.IDLE

    def stop(self) -> None:
        self.status = ExecutionStatus.STOPPED

    def step(self) -> Dict:
        if self.status != ExecutionStatus.RUNNING:
            return {}
        state, _, done, _, _ = self.env.step(None)
        self.current_step += 1
        if done:
            self.status = ExecutionStatus.STOPPED
        return state

    def get_state(self) -> Dict:
        return self.env.get_state()
```

---

## 5. Creating New Factory Proxies

### 5.1 BaseFactoryProxy Interface

All factory proxies must inherit from `BaseFactoryProxy`:

```python
# application/backend/core/BaseFactoryProxy.py

class BaseFactoryProxy:
    """Base class for factory proxy service layer."""

    # Configuration Methods
    def set_config(self, config: dict): ...
    async def initialize(self): ...
    async def cleanup(self): ...

    # Control Methods
    async def start(self): ...
    async def pause(self): ...
    async def reset(self): ...
    async def stop(self): ...

    # Streaming Methods
    async def get_state_events(self) -> list: ...
    async def get_metrics_events(self) -> list: ...
    async def get_control_events(self) -> list: ...
    async def get_state_snapshot(self) -> dict: ...
    async def get_metrics_snapshot(self) -> dict: ...
    async def get_control_status(self) -> dict: ...
```

### 5.2 Creating a New Proxy

**Step 1: Create the Proxy Class**

```python
# application/backend/core/MyFactoryProxy.py

import asyncio
from typing import Optional
from application.backend.core.BaseFactoryProxy import BaseFactoryProxy
from application.backend.core.ProxyFactory import ProxyFactory
from sky_executor.factory_template.factory_core.execution_status import ExecutionStatus

@ProxyFactory.register_proxy("my_factory")
@ProxyFactory.register_proxy("my_factory_alias")  # Optional alias
class MyFactoryProxy(BaseFactoryProxy):
    """Factory proxy for MyFactory"""

    def __init__(self):
        super().__init__()
        self._config = {}
        self._factory = None  # Reference to actual factory
        self._run_task: Optional[asyncio.Task] = None

    def set_config(self, config: dict):
        """Set factory configuration"""
        self._config = config

    async def initialize(self):
        """Initialize the factory proxy"""
        self._state_queue = asyncio.Queue(maxsize=100)
        self._metrics_queue = asyncio.Queue(maxsize=100)
        self._control_queue = asyncio.Queue(maxsize=100)
        self._status = ExecutionStatus.IDLE
        self._current_step = 0

    async def cleanup(self):
        """Cleanup resources"""
        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
        self._status = ExecutionStatus.IDLE
        self._current_step = 0

    async def start(self):
        """Start factory execution"""
        self._status = ExecutionStatus.RUNNING
        self._run_task = asyncio.create_task(self._run_loop())

    async def pause(self):
        """Pause factory execution"""
        self._status = ExecutionStatus.PAUSED

    async def reset(self):
        """Reset factory to initial state"""
        self._status = ExecutionStatus.IDLE
        self._current_step = 0

    async def stop(self):
        """Stop factory execution"""
        self._status = ExecutionStatus.STOPPED
        await self.cleanup()

    async def _run_loop(self):
        """Main execution loop"""
        while self._status == ExecutionStatus.RUNNING:
            try:
                self._current_step += 1
                await asyncio.sleep(1.0)
            except Exception as e:
                print(f"Error in run loop: {e}")
                self._status = ExecutionStatus.ERROR
                break

    async def get_state_snapshot(self) -> dict:
        """Get current state for SSE streaming"""
        return {
            "timestamp": f"T+{self._current_step}s",
            "grid_state": {
                "positions_xy": [[0, 0], [1, 1]],
                "is_active": [True, True],
            },
            "machines": {
                "M1": {"status": "WORKING", "progress": 50},
                "M2": {"status": "IDLE", "progress": 0},
            },
            "active_transfers": [],
            "events": [],
        }

    async def get_metrics_snapshot(self) -> dict:
        """Get current metrics for SSE streaming"""
        return {
            "timestamp": f"T+{self._current_step}s",
            "machine": {"utilization": 0.85, "idle_count": 2, "working_count": 6},
            "agv": {"active_count": 4, "idle_count": 0, "avg_speed": 1.5},
            "job": {"completed": self._current_step, "pending": 10, "in_progress": 5},
        }

    async def get_control_status(self) -> dict:
        """Get control status for SSE streaming"""
        return {
            "status": self._status.value,
            "current_step": self._current_step,
            "total_steps": self._total_steps,
            "is_running": self.is_running(),
        }
```

**Step 2: Register the Proxy**

The proxy is automatically registered via the decorator. The server will discover it on startup.

**Step 3: Add Frontend Configuration**

```javascript
// application/frontend/src/stores/factory.js
const factories = ref([
  // ... existing factories
  {
    id: "my_factory",
    name: "My Custom Factory",
    image: getAssetUrl("my_factory.jpg"),
    description: "Description of my custom factory.",
  },
]);
```

### 5.3 ProxyFactory Registration Methods

```python
from application.backend.core.ProxyFactory import ProxyFactory

# Method 1: Decorator registration
@ProxyFactory.register_proxy("my_factory")
class MyFactoryProxy(BaseFactoryProxy):
    pass

# Method 2: Direct registration
ProxyFactory.register("another_factory", AnotherFactoryProxy)

# Method 3: Create instance
proxy = ProxyFactory.create("my_factory")

# List available proxies
available = ProxyFactory.available()  # ['my_factory', 'static_factory', ...]
```

---

## 6. Frontend-Backend Integration

### 6.1 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stream/state` | GET (SSE) | Factory state stream |
| `/stream/metrics` | GET (SSE) | Metrics stream |
| `/stream/control` | GET (SSE) | Control status stream |
| `/factory/config/upload` | POST | Upload factory configuration |
| `/factory/control/reset` | POST | Reset factory |
| `/factory/control/play` | POST | Start factory |
| `/factory/control/pause` | POST | Pause factory |
| `/factory/control/switch` | POST | Switch factory type |
| `/health` | GET | Health check |
| `/scenario/status` | GET | Scenario connection status |

### 6.2 SSE Data Flow

```
Backend                              Frontend
  |                                     |
  |   GET /stream/state                 |
  |<------------------------------------|
  |                                     |
  |   event: state                      |
  |   data: {"timestamp": "...", ...}   |
  |------------------------------------>|
  |                                     |  store.pushSnapshot(data)
  |                                     |
  |   event: state (next frame)         |
  |   data: {...}                       |
  |------------------------------------>|
  |                                     |
```

### 6.3 Frontend SSE Manager

```javascript
// application/frontend/src/utils/sse.js
export class SSEManager {
  connect(endpoint, options = {}) {
    const { eventTypes = ['message'], onMessage, eventHandlers } = options;
    const eventSource = new EventSource(endpoint);

    eventTypes.forEach(eventType => {
      eventSource.addEventListener(eventType, (event) => {
        const data = JSON.parse(event.data);
        (eventHandlers?.[eventType] || onMessage)?.(data, eventType);
      });
    });

    return connectionId;
  }

  disconnect(connectionId) {
    this.eventSources.get(connectionId)?.close();
  }
}
```

### 6.4 Factory Connection Manager

```javascript
// application/frontend/src/utils/factoryConnection.js
export class FactoryConnectionManager {
  async init(handlers, eventTypes, eventHandlers) {
    this.connections.state = sseManager.connect(
      getApiUrl(API_ROUTES.STREAM_STATE),
      {
        eventTypes: eventTypes.state,
        eventHandlers: eventHandlers.state,
        onMessage: (data) => handlers.onStateUpdate?.(data),
      }
    );

    this.connections.metrics = sseManager.connect(
      getApiUrl(API_ROUTES.STREAM_METRICS),
      {
        eventTypes: eventTypes.metrics,
        eventHandlers: eventHandlers.metrics,
        onMessage: (data) => handlers.onMetricsUpdate?.(data),
      }
    );
  }

  disconnect() {
    Object.values(this.connections).forEach(id => sseManager.disconnect(id));
  }
}
```

### 6.5 State Snapshot Format

```javascript
// Expected state snapshot format
{
  "timestamp": "T+10s",
  "grid_state": {
    "positions_xy": [[5, 2], [3, 4], [7, 1]],  // AGV [x, y] positions
    "is_active": [true, true, false]            // AGV active states
  },
  "machines": {
    "M1": { "status": "WORKING", "progress": 75 },
    "M2": { "status": "IDLE", "progress": 0 },
    "M3": { "status": "BLOCKED", "progress": 30 }
  },
  "active_transfers": [
    { "from": "M1", "to": "M3", "agv": "AGV-1", "progress": 50 }
  ],
  "events": [
    { "type": "info", "title": "Job Started", "message": "..." }
  ]
}
```

---

## 7. Debugging & Troubleshooting

### 7.1 Common Issues

**Issue: Proxy not registered**

```python
# Check available proxies
from application.backend.core.ProxyFactory import ProxyFactory
print(ProxyFactory.available())
```

**Issue: SSE connection drops**

- Check backend logs for errors
- Verify CORS configuration in `server.py`
- Ensure heartbeat messages are being sent

**Issue: Frontend not receiving updates**

```javascript
// Debug SSE connection
eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
};

eventSource.onopen = () => {
  console.log('SSE Connected');
};
```

### 7.2 Development Tips

1. **Use StaticFactoryProxy for testing**: It provides predictable data without needing the full algorithm layer.

2. **Test SSE endpoints with curl**:
   ```bash
   curl -N http://localhost:8000/stream/state
   ```

3. **Monitor asyncio tasks**:
   ```python
   import asyncio
   print(asyncio.all_tasks())
   ```

4. **Frontend Vue DevTools**: Use the Pinia tab to inspect store state.

---

## Quick Reference

### File Locations

| Component | Location |
|-----------|----------|
| Backend Server | `application/backend/server.py` |
| Base Proxy | `application/backend/core/BaseFactoryProxy.py` |
| Proxy Factory | `application/backend/core/ProxyFactory.py` |
| Frontend Store | `application/frontend/src/stores/factory.js` |
| SSE Manager | `application/frontend/src/utils/sse.js` |
| API Utils | `application/frontend/src/utils/api.js` |
| Scenario Tests | `application/frontend/src/scenarios/` |

### Key Commands

```bash
# Backend
uv run uvicorn application.backend.server:app --reload --port 8000

# Frontend
cd application/frontend && npm run dev

# Check proxy registration
uv run python -c "from application.backend.core.ProxyFactory import ProxyFactory; import application.backend.core; print(ProxyFactory.available())"
```

---

For algorithm researchers, see [Client Quick Start Guide](../client/README.md).
