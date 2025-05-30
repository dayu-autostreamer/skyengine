from Scheduler import RandomScheduler
from sky_dag_env import SkyDagEnv

def main():
    # 初始化环境
    env = SkyDagEnv()
    env.create_env()

    LOGGER.info("\n[分配结果]")
    for job_id, job in env.jobs.items():  # 使用 items() 获取 job_id 和 job 对象
        for op in job.operations:
            LOGGER.info(f"Operation {op.id} assigned to Node {op.assigned_node.id}")

    LOGGER.info("\n[运行模拟开始]")
    tick = 0
    unfinished_ops = [op for job in env.jobs for op in job.operations]

    while unfinished_ops:
        LOGGER.info(f"\n--- Tick {tick} ---")
        for op in unfinished_ops:
            if op.state == "pending" and op.is_ready():
                op.assign_to_node(op.assigned_node)

            if op.state == "running":
                op.step()
                LOGGER.info(f"{op.id} running on {op.assigned_node.id}: {op.progress*100:.0f}%")

            if op.state == "finished":
                LOGGER.info(f"{op.id} finished on {op.assigned_node.id}")

        # 过滤已完成
        unfinished_ops = [op for op in unfinished_ops if op.state != "finished"]
        tick += 1

    LOGGER.info("\n✅ 所有操作完成！")

if __name__ == "__main__":
    main()
