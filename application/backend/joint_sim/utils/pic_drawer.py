from pogema.svg_animation.animation_drawer import (
    SvgSettings,
    GridHolder,
    AnimationDrawer,
    Drawing,
)

from pogema.svg_animation.svg_objects import Circle, Rectangle
from pogema import AnimationConfig
import re


def refactor_drawing_render(
    svg_content, possible_color="#FFD700", current_color="#FFA500"
):
    """
    输入 SVG 字符串，输出重构后的 SVG 字符串：
    - 修改 style：删除 .target 类，添加 possible_target 和 current_target
    - 删除 SVG 中所有 <circle class="target" ... />
    """
    # 1️⃣ 提取并修改 <style>
    style_pattern = re.compile(r"<style>(.*?)</style>", re.DOTALL)
    match = style_pattern.search(svg_content)
    if match:
        style_content = match.group(1)
    else:
        style_content = ""

    # 删除 .target 类
    style_content = re.sub(r"\.target\s*\{[^}]*\}", "", style_content)

    # 添加新类，颜色动态
    new_classes = f"""
    .possible_target {{fill: none; stroke: {possible_color}; stroke-width: 10; r: 35;}}
    .current_target {{fill: none; stroke: {current_color}; stroke-width: 10; r: 35;}}
    """

    style_content += new_classes

    # 替换原 SVG 中的 <style>
    svg_content = style_pattern.sub(f"<style>{style_content}</style>", svg_content)

    # 2️⃣ 删除所有 <circle class="target" ... /> 标签
    svg_content = re.sub(r'<circle\s+class="target"[^>]*\/>', "", svg_content)

    return svg_content


def draw_svg(env, timeline):
    """
    渲染 Pogema 环境在给定时间戳的 SVG。
    """
    wr = env.grid_config.obs_radius - 1
    if wr > 0:
        obstacles = env.get_obstacles(ignore_borders=False)[wr:-wr, wr:-wr]
    else:
        obstacles = env.get_obstacles(ignore_borders=False)

    full_history = env.decompress_history(env.get_history())

    current_history = []
    for agent_history in full_history:
        last_state = None
        for s in reversed(agent_history):
            if getattr(s, "step", None) is not None and s.step <= timeline:
                last_state = s
                break
        if last_state is None:
            last_state = agent_history[0]
        current_history.append([last_state])

    svg_settings = SvgSettings()
    agents_colors = {
        index: svg_settings.colors[index % len(svg_settings.colors)]
        for index in range(env.grid_config.num_agents)
    }

    grid_holder = GridHolder(
        width=len(obstacles),
        height=len(obstacles[0]),
        obstacles=obstacles,
        episode_length=1,
        history=current_history,
        obs_radius=env.grid_config.obs_radius,
        on_target=env.grid_config.on_target,
        colors=agents_colors,
        config=AnimationConfig(static=True),
        svg_settings=svg_settings,
    )

    drawing = AnimationDrawer().create_animation(grid_holder)
    return drawing.render()


# 绝对坐标转相对坐标
def get_relative_position(tuples, padding=4):
    if isinstance(tuples, tuple):
        new_tuples = (tuples[0] - padding, tuples[1] - padding)
    else:
        tuple_list = tuples
        new_tuples = []
        for tu in tuple_list:
            tu0 = tu[0] - padding
            tu1 = tu[1] - padding
            new_tuples.append((tu0, tu1))
    return new_tuples


def draw_svg_with_machines_and_targets(
    env,
    timeline: int = 0,
    inactive_color: str = "#F0F0F0",  # 未激活：灰
    active_color: str = "#FFC107",  # 激活：橙
):
    """
    在 Pogema SVG 中叠加机器节点，并高亮当前激活目标。

    Args:
        env: Pogema 环境对象
        timeline: 当前时间步
    """
    # 1️⃣ 绘制基础地图
    wr = env.grid_config.obs_radius - 1
    if wr > 0:
        obstacles = env.get_obstacles(ignore_borders=False)[wr:-wr, wr:-wr]
    else:
        obstacles = env.get_obstacles(ignore_borders=False)

    full_history = env.decompress_history(env.get_history())

    current_history = []
    for agent_history in full_history:
        last_state = None
        for s in reversed(agent_history):
            if getattr(s, "step", None) is not None and s.step <= timeline:
                last_state = s
                break
        if last_state is None:
            last_state = agent_history[0]
        current_history.append([last_state])

    svg_settings = SvgSettings()
    agents_colors = {
        index: svg_settings.colors[index % len(svg_settings.colors)]
        for index in range(env.grid_config.num_agents)
    }

    grid_holder = GridHolder(
        width=len(obstacles),
        height=len(obstacles[0]),
        obstacles=obstacles,
        episode_length=1,
        history=current_history,
        obs_radius=env.grid_config.obs_radius,
        on_target=env.grid_config.on_target,
        colors=agents_colors,
        config=AnimationConfig(static=True),
        svg_settings=svg_settings,
    )

    drawing = AnimationDrawer().create_animation(grid_holder)

    # 这个地方和原先没有差异,可知是下面的裁切部分出问题了
    svg_str = drawing.render()
    # 2️⃣ 删除旧的绘制的目标坐标集合
    new_svg_str = refactor_drawing_render(
        svg_str, possible_color=inactive_color, current_color=active_color
    )

    # 3️⃣ 绘制目标层
    svg_objects = []

    gh: GridHolder = grid_holder
    # 所有可能的目标
    for tx, ty in env.grid_config.possible_targets_xy:
        # tx, ty = env.grid.finishes_xy[agent_idx]
        tx, ty = get_relative_position((tx, ty))
        x, y = ty, gh.width - tx - 1
        possible_settings = {"class": "possible_target"}
        possible_settings.update(
            cx=gh.svg_settings.draw_start + x * gh.svg_settings.scale_size,
            r=gh.svg_settings.r,
            cy=gh.svg_settings.draw_start + y * gh.svg_settings.scale_size,
            stroke=gh.colors[0],
        )
        obj = Circle(**possible_settings)
        svg_objects.append(obj)

    # 当前激活目标
    gh: GridHolder = grid_holder
    for agent_idx, agent_states in enumerate(gh.history):
        tx, ty = agent_states[0].get_target_xy()
        x, y = ty, gh.width - tx - 1
        circle_settings = {"class": "current_target"}
        circle_settings.update(
            cx=gh.svg_settings.draw_start + x * gh.svg_settings.scale_size,
            r=gh.svg_settings.r,
            cy=gh.svg_settings.draw_start + y * gh.svg_settings.scale_size,
            stroke=gh.colors[agent_idx],
        )
        circle_settings.update(stroke=gh.svg_settings.ego_color)
        target = Circle(**circle_settings)
        svg_objects.append(target)

    # 4️⃣ 组合 SVG 层
    machine_layer = "\n".join(obj.render() for obj in svg_objects)
    if "</svg>" in new_svg_str:
        new_svg_str = new_svg_str.replace("</svg>", f"{machine_layer}\n</svg>")
    else:
        new_svg_str += machine_layer

    return new_svg_str


def pretty_print_step(step_idx, actions):
    print(f"\n===== 第 {step_idx + 1} 步 =====")

    # 1️⃣ Job 层动作
    job_actions = actions.get("job_actions", {})
    transfer_reqs = job_actions.get("transfer_requests", [])
    print("【Job 动作】")
    if transfer_reqs:
        for t in transfer_reqs:
            print(f"  - TransferRequest: {t}")
    else:
        print("  (无传输请求)")

    # 2️⃣ Agent 层动作
    agent_actions = actions.get("agent_actions", [])
    print("\n【Agent 动作】")
    if agent_actions:
        for idx, act in enumerate(agent_actions):
            print(f"  - Agent {idx}: 动作 {act}")
    else:
        print("  (无代理动作)")

    # 3️⃣ 任务分配
    assign_actions = actions.get("assign_actions", {})
    assignments = assign_actions.get("assignments", {})

    print("\n【任务分配】")

    if not assignments:
        print("  (无任务分配)")
    else:
        for agv_id, task in assignments.items():
            print(f"  - AGV {agv_id}: 分配任务 {task}")

    pending_transfers = assign_actions.get("pending_transfers", [])
    if pending_transfers:
        print("  待处理传输:")
        for p in pending_transfers:
            print(f"    - {p}")

    print("=============================\n")


def pretty_print_jobs(jobs):
    print("\n================ JOB LIST ================\n")
    for job in jobs:
        print(f"Job ID: {job.job_id}")
        print(f"  Release: {job.release}")
        print(f"  Due:     {job.due}")
        print(f"  Completion Time: {job.completion_time}")
        print("  Operations:")

        for op in job.ops:
            print(
                f"    └─ Op {op.op_id}: "
                f"Machines {op.machine_options}, "
                f"ProcTime={op.proc_time}, "
                f"Status={op.status}, "
                # f"Assigned(machine={op.assigned_machine}, robot={op.assigned_robot}, node={op.assigned_node}), "
                f"Assigned(machine={op.assigned_machine}"
                f"Timing(arrive={op.arrive_machine_at}, start={op.start_process_at}, finish={op.finish_process_at}, wait={op.wait_for_machine_time})"
            )
        print("\n------------------------------------------\n")
