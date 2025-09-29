from typing import List, Optional, Tuple

from sky_executor.packet_factory.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_executor.packet_factory.packet_factory.packet_factory_env.Agv.AGV import AGV
from sky_executor.packet_factory.packet_factory.packet_factory_env.Job.Operation import Operation
from sky_executor.packet_factory.packet_factory.packet_factory_env.Job.Job import Job

INF = float("inf")


def get_min_machine(machines: List[Machine], operation: Operation) -> Machine:
    min_timer = INF
    min_machine: Machine = machines[0]
    for machine in machines:
        if operation.is_machine_available(machine.get_id()) and machine.get_timer() < min_timer:
            min_timer = machine.get_timer()
            min_machine = machine
    return min_machine


def get_min_agv(agvs: List[AGV]) -> AGV:
    min_timer = INF
    min_agv: AGV = agvs[0]
    for agv in agvs:
        if agv.get_timer() < min_timer:
            min_timer = agv.get_timer()
            min_agv = agv
    return min_agv


def main():
    import sys
    input = sys.stdin.read
    data = input().split()
    LOGGER.info(data)
    idx = 0

    n = int(data[idx])
    idx += 1
    m = int(data[idx])
    idx += 1
    k = int(data[idx])
    idx += 1

    jobs: List[Job] = []
    operation_count = 0
    for job_id in range(n):
        num_operations = int(data[idx])
        idx += 1
        operations: List[Operation] = []
        for _ in range(num_operations):
            num_machines = int(data[idx])
            idx += 1
            durations: List[Tuple[int, float]] = []
            for _ in range(num_machines):
                machine_id = int(data[idx])
                idx += 1
                duration = float(data[idx])
                idx += 1
                durations.append((machine_id, duration))
            operations.append(Operation(operation_count, 0.0, durations))
            operation_count += 1
        jobs.append(Job(job_id, operations))

    machines: List[Machine] = []
    for i in range(m):
        x = float(data[idx])
        idx += 1
        y = float(data[idx])
        idx += 1
        machines.append(Machine(i, x, y))

    agvs: List[AGV] = []
    for i in range(k):
        x = float(data[idx])
        idx += 1
        y = float(data[idx])
        idx += 1
        velocity = float(data[idx])
        idx += 1
        agvs.append(AGV(i, x, y, velocity))

    total_timer = 0.0
    for i, job in enumerate(jobs):
        machine: Optional[Machine] = None
        for j in range(job.get_operation_count()):
            op = job.get_operation(j)
            if machine is None and op:
                machine = get_min_machine(machines, op)

            min_agv = get_min_agv(agvs)

            if j == 0 and min_agv and op and machine:
                min_agv.set_operation(op)
                min_agv.unload(machine)
            elif min_agv and machine:
                min_agv.load(machine)
                current_op = min_agv.get_operation()
                if current_op:
                    new_machine = get_min_machine(machines, current_op)
                    if new_machine:
                        min_agv.unload(new_machine)
                        machine = new_machine
            LOGGER.info(
                f"Job {i}, Operation {j}: AGV={min_agv.get_id() if min_agv else -1}, Machine={machine.get_id() if machine else -1}, Duration={op.get_duration(machine.get_id()) if op and machine else 0}")

            if machine:
                total_timer = max(total_timer, machine.get_timer())

    for machine in machines:
        LOGGER.info(f"Machine {machine.get_id()}: {machine.get_timer()}")

    LOGGER.info(f"total makespan: {total_timer:.5f}")


if __name__ == "__main__":
    main()
