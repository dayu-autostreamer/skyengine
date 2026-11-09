"""Regressions for stale reservations, shared ports and finite-buffer admission."""
from __future__ import annotations

import unittest
from sky_executor.session import SimulationSession
from sky_executor.grid_factory.factory.Utils.structure import RoutingTask
from experiment.algorithm_platform_plugins.dfjsp_t.buffer_safety import safe_to_admit
from experiment.algorithm_platform_plugins.dfjsp_t.pibt import PIBTRouter


class BaselineDeadlocksTest(unittest.TestCase):
    def make_environment(self) -> SimulationSession:
        config = {
            "seed": 7, "obs_radius": 2,
            "map": "\n".join(["....."] * 5),
            "topology": {"gridWidth": 5, "gridHeight": 5,
                         "machines": {"M0": {"location": [2, 2]}}},
            "agvs": [{"id": 0, "initialLocation": [2, 2]}],
            "jobs": {"job_list": [
                {"job_id": 0, "priority": 200,
                 "operations": [{"machine_options_with_time": [[0, 2]]}]},
                {"job_id": 1, "priority": 100,
                 "operations": [{"machine_options_with_time": [[0, 10]]}]},
            ]},
            "material_handling_config": {"raw_material_source": [2, 2],
                                         "finished_goods_destination": [4, 4]},
        }
        session = SimulationSession.from_config(config, native_actions=True, headless=True)
        self.addCleanup(session.close)
        return session

    def test_same_machine_urgent_arrival_releases_reservation(self):
        session = self.make_environment()
        requests = [{"task_id": jid, "job_id": jid, "op_id": 0,
                     "source": (2, 2), "destination": (2, 2), "ready_time": 0,
                     "priority": priority} for jid, priority in ((0, 200), (1, 100))]
        session.step({"job_actions": {"transfer_requests": requests}})
        state = session.env.state
        self.assertEqual(state.machines[0].urgent_reservations, set())
        self.assertEqual(state.jobs[0].ops[0].status, "PROCESSING")
        session.step({})
        self.assertEqual(state.jobs[0].ops[0].status, "FINISHED")
        session.step({})
        normal = state.jobs[1].ops[0]
        self.assertEqual(normal.status, "PROCESSING")
        self.assertIs(state.machines[0].current_op, normal)

    def test_full_dropoff_does_not_lock_vehicle_on_port(self):
        session = self.make_environment()
        env = session.env.state
        machine = env.machines[0]
        machine.buffer_capacity = 1
        machine.buffer_jobs = {9}
        task = RoutingTask(task_id=0, job_id=0, op_id=0, source=(0, 0),
                           destination=(2, 2), ready_time=0, assigned_agent_id=0)
        env.agv_current_task[0] = task
        env.active_transfers.append(task)
        env.agv_loaded[0] = True
        env.agv_task_phase[0] = "TO_DROPOFF"
        env.jobs[0].carrier_id = 0
        env.jobs[0].material_location = None
        env.jobs[0].transport_task_id = task.task_id
        session.step({"agent_actions": [0]})
        self.assertEqual(env.agv_task_phase[0], "TO_DROPOFF")
        self.assertEqual(env.agv_handling_remaining[0], 0)
        before = tuple(env.grid.positions_xy[0])
        session.step({"agent_actions": [1]})
        self.assertNotEqual(tuple(env.grid.positions_xy[0]), before)
        self.assertTrue(env.agv_loaded[0])
        self.assertEqual(machine.buffer_jobs, {9})

    def test_bankers_admission_prevents_circular_material_wait(self):
        def op(oid, mid, status="PENDING"):
            return {"op_id": oid, "status": status, "assigned_machine": mid if status == "FINISHED" else None,
                    "machine_options_with_time": [[mid, 1]]}
        state = {"machines": [{"id": 0, "buffer_capacity": 1}, {"id": 1, "buffer_capacity": 1}],
                 "jobs": [{"job_id": 0, "ops": [op(0, 0, "FINISHED"), op(1, 1)]},
                          {"job_id": 1, "ops": [op(0, 1), op(1, 0)]}]}
        claims = {0: {0}, 1: set()}
        self.assertFalse(safe_to_admit(state, claims, 1, 0, 1))
        self.assertTrue(safe_to_admit(state, claims, 0, 1, 1))
        self.assertEqual(claims, {0: {0}, 1: set()})

    def test_pibt_yields_idle_port_without_vertex_or_edge_collision(self):
        task = {"task_id": 0, "source": [2, 2], "destination": [4, 4], "kind": "finished_goods"}
        agents = [{"id": 0, "pos": [2, 1], "current_task": task, "task_phase": "TO_PICKUP", "status": "OK"},
                  {"id": 1, "pos": [2, 2], "current_task": None, "task_phase": "IDLE", "status": "OK"}]
        state = {"grid": [[0] * 5 for _ in range(5)], "moves": [[0, 0], [-1, 0], [1, 0], [0, -1], [0, 1]],
                 "agents": agents, "machines": [{"location": [2, 2], "buffer_jobs": [0], "buffer_capacity": 1}],
                 "jobs": []}
        route = PIBTRouter(7).plan(state, set())
        next_positions = []
        for agent, move in zip(agents, route):
            dx, dy = state["moves"][move["path"][0]]
            next_positions.append((agent["pos"][0] + dx, agent["pos"][1] + dy))
        self.assertEqual(next_positions[0], (2, 2))
        self.assertNotEqual(next_positions[1], (2, 2))
        self.assertNotEqual(next_positions[1], (2, 1))


if __name__ == "__main__":
    unittest.main()
