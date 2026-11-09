"""Material configuration and reset data shared by initial and inserted jobs."""


def traversable(state, cell):
    x, y = state._to_internal_xy(cell)
    grid = state.grid.obstacles
    return 0 <= x < grid.shape[0] and 0 <= y < grid.shape[1] and grid[x, y] == 0



def initialize_job_material(state, job):
    source = job.raw_material_source if job.raw_material_source is not None else state.raw_material_source
    destination = (job.finished_goods_destination if job.finished_goods_destination is not None
                   else state.finished_goods_destination)
    job.raw_material_source = tuple(source)
    job.finished_goods_destination = tuple(destination)
    job.material_location = job.raw_material_source
    job.carrier_id = job.transport_task_id = None
    job.delivered = False
    job.completion_time = -1.0


def initialize_material_stations(state, reachable=None):
    offset = state.grid_config.obs_radius or 0
    cells = [state._to_public_xy((x, y))
             for x in range(offset, state.grid.obstacles.shape[0] - offset)
             for y in range(offset, state.grid.obstacles.shape[1] - offset)
             if state._to_public_xy((x, y)) not in state.hash_machines
             and (reachable is None or state._to_public_xy((x, y)) in reachable)
             and traversable(state, state._to_public_xy((x, y)))]
    if not cells:
        raise ValueError("layout needs a traversable material station outside the machines")
    if state.raw_material_source is None:
        state.raw_material_source = cells[0]
    if state.finished_goods_destination is None:
        state.finished_goods_destination = cells[-1]
    for job in state.jobs:
        initialize_job_material(state, job)
