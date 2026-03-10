# Algorithm Researcher Quick Start Guide

This guide is for algorithm researchers who want to use SkyEngine environments for algorithm demonstration, data collection, and reinforcement learning training.

## Table of Contents

1. [Overview](#1-overview)
2. [Environment Setup](#2-environment-setup)
3. [Running Simulations](#3-running-simulations)
4. [Data Collection](#4-data-collection)
5. [Algorithm Integration](#5-algorithm-integration)
6. [Visualization & Monitoring](#6-visualization--monitoring)

---

## 1. Overview

SkyEngine provides a flexible manufacturing simulation environment that follows Gymnasium/PettingZoo conventions, making it suitable for:

 algorithm demonstration and data collection, and reinforcement learning training.

### Key Features

- **Gymnasium-compatible interface**: Standard `reset()`, `step()`, `render()` methods
- **Multi-agent support**: PettingZoo ParallelEnv for multi-AGV coordination
- **Pluggable components**: JobSolver, Assigner, RouteSolver
- **Real-time visualization**: SSE streaming to frontend

---

## 2. Environment Setup

### 2.1 Basic Usage

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

# Create factory
factory = GridFactory(config)

# Initialize
factory.initialize()

# Run simulation
factory.start()

# Pause/Resume
factory.pause()
factory.start()

# Reset
factory.reset()

# Stop
factory.stop()

# Cleanup
factory.cleanup()
```

### 2.2 Configuration Options

```python
@dataclass
class GridFactoryConfig:
    # Agent configuration
    num_agents: int = 4
    agent_speed: float = 1.0

    # Grid configuration
    grid_size: int = 8

    # Machine configuration
    num_machines: int = 8
    machine_layout: str = "default"

    # Job configuration
    num_jobs: int = 6
    job_complexity: str = "medium"

    # Algorithm selection
    job_solver: str = "greedy"  # Options: greedy, priority, duel, transformer
    assigner: str = "ortools"  # Options: random, greedy, nearest, load_balance, ortools
    route_solver: str = "astar"  # Options: astar, greedy, instant

    # Execution parameters
    step_interval: float = 1.0
    max_steps: int = 1000
    random_seed: int = None
```

### 2.3 Available Algorithms

| Component | Options | Description |
|-----------|--------|-------------|
| **JobSolver** | greedy, priority, duel, transformer | Job scheduling algorithms |
| **Assigner** | random, greedy, nearest, load_balance, ortools | Task-AGV assignment strategies |
| **RouteSolver** | astar, greedy, instant | Multi-agent pathfinding algorithms |

---

## 3. Running Simulations

### 3.1 Basic Simulation Loop

```python
from sky_executor.grid_factory.factory.grid_factory import GridFactory, GridFactoryConfig

# Setup
config = GridFactoryConfig(num_agents=4, grid_size=8)
factory = GridFactory(config)
factory.initialize()
factory.start()

# Access environment
env = factory.env

# Step through simulation
for step in range(100):
    # Get observation
    observation = env.get_state()

    # Make decision (example: random actions)
    actions = {
        agent_id: random.randint(0, config.num_agents),
        target: random.randint(0, config.grid_size)
    }

    # Step environment
    obs, reward, done, truncated, info = env.step(actions)

    if done:
        print(f"Episode finished at step {step}")
        break

# Cleanup
factory.stop()
factory.cleanup()
```

### 3.2 With Custom Algorithms

```python
from sky_executor.grid_factory.factory.grid_factory import GridFactory, GridFactoryConfig
from sky_executor.grid_factory.factory.Component import AssignerFactory, RouteSolverFactory

# Create custom assigner
@AssignerFactory.register("my_assigner")
class MyAssigner:
    def assign(self, env):
        # Custom assignment logic
        assignments = self._compute_assignments(env)
        return assignments

# Create custom route solver
@RouteSolverFactory.register("my_router")
class MyRouteSolver:
    def solve(self, env, assignments):
        # Custom routing logic
        routes = self._compute_routes(env, assignments)
        return routes

# Use custom algorithms
config = GridFactoryConfig(
    num_agents=4,
    grid_size=8,
    assigner="my_assigner",
    route_solver="my_router",
)
```

### 3.3 Recording Trajectories

```python
import json
from pathlib import Path

# During simulation
trajectory = {
    "observations": [],
    "actions": [],
    "rewards": [],
    "dones": [],
    "infos": []
}

# In your step loop
for step in range(100):
    obs = env.get_state()
    action = your_algorithm.get_action(obs)
    next_obs, reward, done, _, info = env.step(action)

    # Record
    trajectory["observations"].append(obs)
    trajectory["actions"].append(action)
    trajectory["rewards"].append(reward)
    trajectory["dones"].append(done)
    trajectory["infos"].append(info)

# Save trajectory
output_path = Path("trajectories/my_trajectory.json")
with open(output_path, "w") as f:
    json.dump(trajectory, f, indent=2)
```

---

## 4. Data Collection

### 4.1 Trajectory Format

```python
# Standard trajectory format
trajectory = {
    "metadata": {
        "episode_id": "unique_id",
        "timestamp": "2024-01-01T00:00:00",
        "config": {
            "num_agents": 4,
            "grid_size": 8,
            # ... other config
        }
    },
    "data": {
        "observations": [
            # Observation at each step
            {"step": 0, "agv_positions": [...], "machine_states": {...}},
            {"step": 1, "agv_positions": [...], "machine_states": {...}},
            # ...
        ],
        "actions": [
            # Actions taken at each step
            {"step": 0, "agent_id": 0, "target": [3, 4]},
            {"step": 1, "agent_id": 1, "target": [5, 6]},
            # ...
        ],
        "rewards": [
            # Reward at each step
            1.0, 0.5, -0.2, ...
        ],
        "dones": [
            # Done flags
            False, False, True, ...
        ],
        "infos": [
            # Additional info
            {"step": 0, "jobs_completed": 0},
            # ...
        ]
    }
}
```

### 4.2 Expert Data Collection

For imitation learning, collect expert trajectories using OR-Tools:

```python
from sky_executor.grid_factory.factory.grid_factory import GridFactory, GridFactoryConfig

config = GridFactoryConfig(
    num_agents=4,
    grid_size=8,
    assigner="ortools",  # Expert assigner
    route_solver="astar",  # Expert router
)
factory = GridFactory(config)
factory.initialize()

trajectories = []

# Collect multiple episodes
for episode in range(100):
    factory.reset()
    factory.start()

    trajectory = {
        "observations": [],
        "actions": [],
        "rewards": []
    }

    while factory.is_running():
        obs = factory.env.get_state()

        # Get expert action (from OR-Tools)
        action = factory.coordinator.get_expert_action(obs)

        next_obs, reward, done, _, info = factory.env.step(action)

        trajectory["observations"].append(obs)
        trajectory["actions"].append(action)
        trajectory["rewards"].append(reward)

        if done:
            break

    trajectories.append(trajectory)
    factory.stop()

# Save trajectories
import json
with open("expert_trajectories.json", "w") as f:
    json.dump(trajectories, f, indent=2)
```

---

## 5. Algorithm Integration

### 5.1 Implementing a New Algorithm

```python
from sky_executor.grid_factory.factory.Component import (
    BaseAssigner,
    AssignerFactory,
    AssignResult,
)
 from dataclasses import dataclass

@dataclass
class MyAssignResult(AssignResult):
    assignments: dict
    execution_time: float

@AssignerFactory.register("my_algorithm")
class MyAlgorithmAssigner(BaseAssigner):
    """Custom assignment algorithm"""

    def __init__(self, config=None):
        self.config = config or {}

    def assign(self, env) -> AssignResult:
        # Get environment state
        state = env.get_state()

        # Your algorithm logic here
        pending_tasks = state.get("pending_tasks", [])
        available_agvs = state.get("available_agvs", [])

        assignments = {}
        for task in pending_tasks:
            # Your assignment logic
            best_agv = self._find_best_agv(task, available_agvs)
            if best_agv:
                assignments[task.id] = best_agv.id

        return MyAssignResult(
            assignments=assignments,
            execution_time=0.1
        )

    def _find_best_agv(self, task, agvs):
        # Example: nearest AGV
        min_distance = float('inf')
        best_agv = None

        for agv in agvs:
            distance = self._calculate_distance(task.position, agv.position)
            if distance < min_distance:
                min_distance = distance
                best_agv = agv

        return best_agv

    def _calculate_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
```

### 5.2 Using with Reinforcement Learning

```python
import torch
import torch.nn as nn
from sky_executor.grid_factory.factory.grid_factory import GridFactory, GridFactoryConfig

# Define your RL model
class PolicyNetwork(nn.Module):
    def __init__(self, obs_dim, action_dim):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(obs_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
        )

    def forward(self, x):
        return self.network(x)

# Create RL assigner
@AssignerFactory.register("rl_assigner")
class RLAssigner(BaseAssigner):
    def __init__(self, model_path=None):
        self.model = PolicyNetwork(obs_dim=64, action_dim=4)
        if model_path:
            self.model.load_state_dict(torch.load(model_path))

    def assign(self, env) -> AssignResult:
        state = env.get_state()
        obs = self._preprocess(state)

        with torch.no_grad():
            action_probs = self.model(torch.FloatTensor(obs))
            action = torch.argmax(action_probs).item()

        # Convert to assignment
        assignments = self._action_to_assignment(action, env)
        return MyAssignResult(assignments=assignments, execution_time=0.05)

    def _preprocess(self, state):
        # Preprocess state for model input
        return torch.FloatTensor(state.flatten())

    def _action_to_assignment(self, action, env):
        # Convert model output to assignment
        pass
```

---

## 6. Visualization & Monitoring

### 6.1 Real-time Monitoring

```python
from sky_executor.grid_factory.factory.Metrics import MetricsMonitorFactory

# Create monitors
monitors = MetricsMonitorFactory.create_monitors([
    "agv_metrics",
    "job_metrics",
    "congestion",
])

# During simulation
for step in range(100):
    # ... simulation step ...

    # Update monitors
    for monitor in monitors:
        metrics = monitor.update(env)
        print(f"Step {step}: {metrics}")
```

### 6.2 Visualization Options

| Monitor Type | Description |
|--------------|-------------|
| AGVMetricsMonitor | AGV utilization, active/idle counts |
| JobDueMonitor | Job completion rates, due dates |
| CongestionHeatmapMonitor | Grid congestion visualization |
| RouteTimeSeriesMonitor | Route efficiency over time |
| StatsSaveMonitor | Save metrics to file |

### 6.3 Frontend Visualization

Access the frontend at `http://localhost:5173` to see:
- Real-time AGV positions
- Machine status indicators
- Performance metrics dashboard
- Event timeline

---

## Quick Reference

### Key Files

| File | Description |
|------|-------------|
| `sky_executor/grid_factory/factory/grid_factory.py` | Main factory class |
| `sky_executor/grid_factory/factory/grid_factory_env.py` | Environment implementation |
| `sky_executor/grid_factory/factory/Component/` | Algorithm components |
| `sky_executor/grid_factory/factory/Metrics/` | Monitoring tools |

### Common Commands

```bash
# Run simulation
python -m sky_executor.grid_factory.factory.grid_factory

# Collect trajectories
python scripts/collect_expert_trajectories.py --expert_type ortools --num_episodes 100

# Train model
python scripts/train_assigner.py --traj_dir trajectories/ --num_epochs 100

# Evaluate
python scripts/evaluate_rl_solver.py --model_path checkpoints/model.pt
```

### Environment Interface

```python
class BaseEnvironment:
    def reset(self, seed=None) -> Tuple[obs, info]: ...
    def step(self, action) -> Tuple[obs, reward, done, truncated, info]: ...
    def get_state(self) -> Dict: ...
    def set_state(self, state: Dict) -> None: ...
    def render(self) -> Any: ...
```

---

For platform developers, see [Developer Guide](../developer/README.md).
