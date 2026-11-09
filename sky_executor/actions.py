"""Public decision representations shared by sessions and control entry points."""
from copy import deepcopy

from sky_executor.grid_factory.factory.Utils.structure import RoutingTask


def normalize_action(actions: dict) -> dict:
    """Copy JSON/object actions without looking up or changing business state."""
    result = deepcopy(dict(actions or {}))
    job = dict(result.get("job_actions") or {})
    job["transfer_requests"] = [
        item.dict() if isinstance(item, RoutingTask) else dict(item)
        for item in job.get("transfer_requests") or ()
    ]
    assign = dict(result.get("assign_actions") or {})
    assign["assignments"] = {
        int(agent_id): value if value is None or isinstance(value, (RoutingTask, dict)) else int(value)
        for agent_id, value in (assign.get("assignments") or {}).items()
    }
    assign["pending_transfers"] = [
        item.dict() if isinstance(item, RoutingTask) else dict(item)
        for item in assign.get("pending_transfers") or ()
    ]
    result.update(job_actions=job, assign_actions=assign,
                  agent_actions=list(result.get("agent_actions") or ()))
    return result
