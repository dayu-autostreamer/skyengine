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

    svg_str = drawing.render()

    # 2️⃣ 获取当前激活目标坐标集合
    new_svg_str = refactor_drawing_render(
        svg_str, possible_color=inactive_color, current_color=active_color
    )

    #  利用当前激活的targets和可能的targets生成最终的 svg 字符串
    # 3️⃣ 绘制目标层
    svg_objects = []

    current_settings = {"class": "current_target"}
    # 当前激活目标
    for tx, ty in env.grid.finishes_xy:
        cx = (
            grid_holder.svg_settings.draw_start
            + (ty - 1) * grid_holder.svg_settings.scale_size
        )
        cy = (
            grid_holder.svg_settings.draw_start
            + (grid_holder.width - tx) * grid_holder.svg_settings.scale_size
        )
        current_settings.update(
            cx=cx,
            cy=cy,
            r=grid_holder.svg_settings.r,
            stroke=active_color,
            fill="none",
        )
        obj = Circle(**current_settings)
        svg_objects.append(obj)

    possible_settings = {"class": "possible_target"}
    # 可能目标
    for tx, ty in env.grid_config.possible_targets_xy:
        # 如果已经是激活目标，就跳过
        if (tx, ty) in env.grid.finishes_xy:
            continue
        cx = grid_holder.svg_settings.draw_start + (ty - 1) * svg_settings.scale_size
        cy = (
            grid_holder.svg_settings.draw_start
            + (grid_holder.width - tx) * svg_settings.scale_size
        )
        possible_settings.update(
            cx=cx,
            cy=cy,
            r=grid_holder.svg_settings.r,
            stroke=inactive_color,
            fill="none",
        )
        obj = Circle(**possible_settings)
        svg_objects.append(obj)

    # 4️⃣ 组合 SVG 层
    machine_layer = "\n".join(obj.render() for obj in svg_objects)
    if "</svg>" in new_svg_str:
        new_svg_str = new_svg_str.replace("</svg>", f"{machine_layer}\n</svg>")
    else:
        new_svg_str += machine_layer

    return new_svg_str
