"""
@Project ：SkyEngine
@File    ：draw_metrics.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 22:04
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def plot_machine_gantt(machine_schedule, machines, title="Machine Gantt"):
    fig, ax = plt.subplots(figsize=(10, 3 + len(machines) * 0.25))
    y_labels = []
    for i, m in enumerate(machines):
        tasks = sorted(machine_schedule.get(m.id, []), key=lambda x: x[0])
        for s, e, jid, oid in tasks:
            ax.barh(i, e - s, left=s, height=0.6)
            ax.text(
                s + 0.02 * (e - s + 1), i, f"J{jid}-O{oid}", va="center", fontsize=8
            )
        y_labels.append(f"M{m.id}")
    ax.set_yticks(list(range(len(machines))))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Time")
    ax.set_title(title)
    plt.tight_layout()
    plt.show()


def plot_machine_util_bar(stats):
    util = stats["machine_util"]
    mids = sorted(util.keys())
    vals = [util[m] for m in mids]
    plt.figure(figsize=(6, 3))
    plt.bar([f"M{m}" for m in mids], vals)
    plt.title("Machine Utilization")
    plt.ylim(0, 1)
    plt.show()


def draw_beautiful_gantt(
    schedule, machines, makespan, rule_name, title="Job Shop Schedule"
):
    """
    使用 Matplotlib 绘制美观的甘特图
    """
    # makespan = result.stats["makespan"]
    # rule_name = result.stats.get("rule", "Unknown")

    fig, ax = plt.subplots(figsize=(12, 6))

    # 颜色映射 (Tab20 适合区分不同的 Job)
    cmap = plt.get_cmap("tab20")

    # 设定 Y 轴
    m_ids = [m.id for m in machines]
    m_ids.sort(reverse=True)  # 机器 0 在最上面不太符合直觉，通常倒序排列

    # 绘制 Bar
    for m_id, tasks in schedule.items():
        for start, end, job_id, op_id in tasks:
            duration = end - start
            color = cmap(job_id % 20)

            # 绘制矩形
            # barh(y, width, left=x)
            rect = ax.barh(
                m_id,
                duration,
                left=start,
                height=0.6,
                align="center",
                color=color,
                edgecolor="black",
                alpha=0.85,
            )

            # 添加文字标签 (居中)
            # 如果色块太小，就不显示文字
            if duration > (makespan * 0.02):
                ax.text(
                    start + duration / 2,
                    m_id,
                    f"J{job_id}\nO{op_id}",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=8,
                    fontweight="bold",
                )

    # 美化图表
    ax.set_yticks(m_ids)
    ax.set_yticklabels([f"Machine {i}" for i in m_ids], fontsize=10, fontweight="bold")
    ax.set_xlabel("Time", fontsize=11)
    ax.set_title(
        f"{title} (Rule: {rule_name}, Makespan: {makespan:.1f})",
        fontsize=14,
        fontweight="bold",
    )

    # 设置 X 轴范围
    ax.set_xlim(0, makespan * 1.05)

    # 添加网格线 (垂直)
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    # 创建图例 (只显示 Job)
    # 获取唯一的 job_id
    unique_jobs = set()
    for tasks in schedule.values():
        for t in tasks:
            unique_jobs.add(t[2])

    patches = [
        mpatches.Patch(color=cmap(j % 20), label=f"Job {j}")
        for j in sorted(unique_jobs)
    ]
    ax.legend(handles=patches, bbox_to_anchor=(1.01, 1), loc="upper left", title="Jobs")

    plt.tight_layout()
    plt.show()
