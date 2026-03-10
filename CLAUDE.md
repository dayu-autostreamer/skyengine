# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TianGong (天工)** is a flexible manufacturing simulation-integrated scheduling platform (SkyEngine v1.0.0). It combines high-fidelity simulation with scheduling algorithms for production decision systems.

## Architecture

The system follows a **two-layer decoupled architecture**:

```
Service Layer (application/)
  - FastAPI REST API + SSE streaming (port 8000)
  - Vue.js frontend with ECharts visualization
  - FactoryProxy bridges service and algorithm layers

Algorithm Layer (sky_executor/)
  - factory_template/     # Abstract interfaces for factories
  - Pluggable scheduling components
  - RL training framework
```

**Key principle**: Service layer does not contain scheduling logic; algorithm layer does not depend on business interfaces.

### Factory Template Abstraction

The `factory_template` module provides abstract interfaces for all factory types:

```python
from sky_executor.factory_template import (
    BaseFactory,          # Abstract factory manager
    BaseEnvironment,      # Abstract environment (Gymnasium-like)
    ExecutionStatus,      # Factory execution states
    BaseCallback,         # Lifecycle callbacks
    BaseEvent,            # Events for SSE streaming
    NamespaceRegistry,    # Namespace-based component registry
)
```

Key classes:
- **ExecutionStatus**: Enum with states (IDLE, RUNNING, PAUSED, STOPPED, ERROR)
- **BaseEnvironment**: Abstract environment with reset/step/render/get_state/set_state
- **BaseFactory**: Abstract factory manager with lifecycle methods
- **BaseCallback**: Hook into factory lifecycle events
- **NamespaceRegistry**: Register components by namespace and name

### GridFactory Implementation

GridFactory is the primary factory implementation:

```python
from sky_executor.grid_factory.factory.grid_factory import GridFactory, GridFactoryConfig

# Create configuration
config = GridFactoryConfig(
    num_agents=4,
    grid_size=8,
    num_machines=8,
    num_jobs=6,
    job_solver="greedy",
    assigner="ortools",
    route_solver="astar",
    step_interval=1.0,
)

# Create and use factory
factory = GridFactory(config)
factory.initialize()
factory.start()   # Run in background thread
factory.pause()   # Pause execution
factory.reset()   # Reset to initial state
factory.stop()    # Stop execution
factory.cleanup() # Release resources
```

## Common Commands

### Backend (FastAPI)
```bash
cd application/backend
uvicorn application.backend.server:app --reload --port 8000
```

### Frontend (Vue.js)
```bash
cd application/frontend
npm install
npm run dev      # Development server
npm run build    # Production build
```

### RL Training Pipeline
```bash
# 1. Collect expert trajectories
python scripts/collect_expert_trajectories.py --expert_type ortools --num_episodes 100

# 2. Train Assigner model
python scripts/train_assigner.py --traj_dir expert_trajectories/ortools --num_epochs 100 --device cuda

# 3. Train Route Solver model
python scripts/train_route_solver.py --traj_dir expert_trajectories/mapf_gpt --use_cnn --device cuda

# 4. Evaluate models
python scripts/evaluate_rl_solver.py --assigner_model checkpoints/assigner_bc/checkpoint_best.pt

# Monitor training with TensorBoard
tensorboard --logdir logs/
```

### Dependencies
```bash
# Python dependencies (uses uv)
uv sync

# Frontend dependencies
cd application/frontend && npm install
```

## Core Components

### Algorithm Components (sky_executor/grid_factory/factory/Component/)

Four pluggable component types with unified interfaces:

1. **JobSolver** (`JobSolver/`): Task/job scheduling (JSSP)
2. **Assigner** (`Assigner/`): Task-to-AGV assignment
   - Implementations: random, greedy, nearest, least_congestion, load_balance, ortools, rl
3. **RouteSolver** (`RouteSolver/`): Multi-agent pathfinding (MAPF)
   - Implementations: astar, greedy, instant, mapf_gpt, rl
4. **Coordinator** (`Coordinator/`): Integrates all component decisions

### Component Registry Pattern

Components use a decorator-based registry:

```python
from sky_executor.grid_factory.factory.Component import AssignerFactory

@AssignerFactory.register("my_assigner")
class MyAssigner(BaseAssigner):
    def assign(self, env) -> AssignResult:
        ...

# Usage via string name
coordinator = Coordinator(assigner="my_assigner")
```

### Factory Types

- **GridFactory**: Grid-based manufacturing with AGV pathfinding (primary)
  - Implements `BaseFactory` interface
  - Manages `GridFactoryEnv` (extends `BaseEnvironment` + PettingZoo `ParallelEnv`)
  - Threading-based execution with start/pause/stop/reset lifecycle
  - Uses `Coordinator` for solver orchestration

### Service Layer (Application Layer)

The service layer wraps sync factories for async execution:

```python
# GridFactoryProxy wraps GridFactory for async/SSE
from application.backend.core.GridFactoryProxy import GridFactoryProxy

proxy = GridFactoryProxy()
proxy.set_config(config_dict)
await proxy.initialize()
await proxy.start()  # Starts async execution loop
state = await proxy.get_state_snapshot()  # For SSE streaming
await proxy.cleanup()
```

## Key Directories

```
sky_executor/
├── factory_template/           # Abstract factory interfaces
│   ├── factory_core/           # BaseFactory, BaseEnvironment, ExecutionStatus
│   ├── callback/               # BaseCallback for lifecycle hooks
│   ├── event/                  # BaseEvent for SSE streaming
│   └── registry/               # NamespaceRegistry for component registration
├── grid_factory/
│   └── factory/
│       ├── grid_factory.py     # GridFactory class (implements BaseFactory)
│       ├── grid_factory_env.py # GridFactoryEnv (implements BaseEnvironment)
│       ├── Component/          # Pluggable algorithm components
│       ├── Utils/              # Shared utilities
│       ├── problem/            # Problem definitions
│       ├── trajectory/         # RL trajectory recording
│       └── training/           # Training utilities

application/
├── backend/
│   ├── core/
│   │   ├── BaseFactoryProxy.py # Base async proxy interface
│   │   ├── GridFactoryProxy.py # Async wrapper for GridFactory
│   │   └── ProxyFactory.py     # Factory registration
│   └── server.py               # Main entry point
└── frontend/                   # Vue.js + Element Plus

scripts/                        # Training/evaluation scripts
docs/                           # Documentation (RL_TRAINING.md, etc.)
```

## Data Flow

```
Environment → Observation → Coordinator → Actions → Environment
                ↓                           ↓
            Problem                    Solution
```

Coordinator orchestrates: `Job Scheduling → Task Assignment → Path Planning`

## Code Conventions

- Python 3.11+ with type hints
- Component classes inherit from base classes (BaseAssigner, BaseRouteSolver, etc.)
- Results returned as dataclasses (AssignResult, RouteResult, etc.)
- Use `@dataclass` for result types
- Registry pattern for component discovery

## Dependencies

Key packages (see pyproject.toml):
- fastapi, uvicorn, tornado (web/streaming)
- torch (deep learning)
- ortools (optimization)
- gymnasium, pettingzoo (RL environments)
- pogema (MAPF benchmark)
