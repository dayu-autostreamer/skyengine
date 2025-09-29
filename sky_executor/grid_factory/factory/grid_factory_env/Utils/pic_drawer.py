from pogema.svg_animation.animation_drawer import SvgSettings, GridHolder, AnimationDrawer
from pogema.svg_animation.svg_objects import Circle, Rectangle
from pogema import AnimationConfig
from typing import List, Union


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
        svg_settings=svg_settings
    )

    animation = AnimationDrawer().create_animation(grid_holder)
    return animation.render()

def draw_svg_with_machines_and_targets(env,
                                       machines: List[Union[tuple, object]],
                                       timeline: int = 0,
                                       shape: str = "circle",
                                       inactive_color: str = "#A9A9A9",  # 未激活：灰
                                       active_color: str = "#FF8C00",    # 激活：橙
                                       active_opacity: float = 0.85,
                                       inactive_opacity: float = 0.6,
                                       stroke_color: str = "black",
                                       stroke_width: float = 0.02):
    """
    在 Pogema SVG 中叠加机器节点，并高亮当前激活目标。

    Args:
        env: Pogema 环境对象
        machines: 机器对象列表（[(x, y), ...] 或 [Machine(...), ...]）
        timeline: 当前时间步
        shape: 机器绘制形状 ('circle' 或 'rect')
        inactive_color: 未激活机器颜色
        active_color: 被指派目标的颜色
        active_opacity: 激活机器的不透明度
        inactive_opacity: 未激活机器的不透明度
        stroke_color: 边框颜色
        stroke_width: 边框线宽
    """
    # 1️⃣ 绘制基础地图
    svg_str = draw_svg(env, timeline)

    # 2️⃣ 获取当前激活目标坐标集合
    active_targets = set(tuple(pos) for pos in env.grid.finishes_xy)

    svg_objects = []
    for m in machines:
        # --- 提取坐标 ---
        if hasattr(m, "location"):
            x, y = m.location  # Machine 对象
        elif isinstance(m, (tuple, list)) and len(m) == 2:
            x, y = m
        else:
            raise TypeError(f"Unsupported machine type: {type(m)}")

        # --- 判断激活状态 ---
        is_active = (x, y) in active_targets

        # --- 坐标转换（行列翻转）---
        cx, cy = y + 0.5, x + 0.5

        # --- 绘制 ---
        if shape == "circle":
            obj = Circle(
                cx=cx,
                cy=cy,
                r=0.35,
                fill=active_color if is_active else inactive_color,
                opacity=active_opacity if is_active else inactive_opacity,
                stroke=stroke_color,
                stroke_width=stroke_width
            )
        elif shape == "rect":
            obj = Rectangle(
                x=y + 0.1,
                y=x + 0.1,
                width=0.8,
                height=0.8,
                fill=active_color if is_active else inactive_color,
                opacity=active_opacity if is_active else inactive_opacity,
                stroke=stroke_color,
                stroke_width=stroke_width
            )
        else:
            raise ValueError(f"Unknown shape '{shape}'")

        svg_objects.append(obj)

    # 3️⃣ 组合 SVG 层
    machine_layer = "\n".join(obj.render() for obj in svg_objects)

    if "</svg>" in svg_str:
        svg_str = svg_str.replace("</svg>", f"{machine_layer}\n</svg>")
    else:
        svg_str += machine_layer

    return svg_str