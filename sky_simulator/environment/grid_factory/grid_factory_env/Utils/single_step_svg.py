import os
from pogema import GridConfig, pogema_v0, AnimationMonitor, AnimationConfig, BatchAStarAgent
from pogema.wrappers.persistence import AgentState
from pogema.svg_animation.animation_drawer import SvgSettings, GridHolder, AnimationDrawer
import config
from config.all_field_const import CacheInfo
from sky_logs.dc_helper import DiskCacheHelper


class SingleStepAnimationMonitor(AnimationMonitor):
    """
    扩展 AnimationMonitor，修复每步保存同一帧的问题：
    - 在 step() 中先递增 current_step 再保存
    - 在 save_step_svg() 中为每个 agent 只取当前时刻的最后一个状态（构造成长度为1的历史）
    """

    def __init__(self, env, animation_config=AnimationConfig(), save_dir=config.STEPS_DIR):
        super().__init__(env, animation_config)
        self.save_dir = save_dir
        self.current_step = 0
        self.dh = DiskCacheHelper(expire=CacheInfo.CACHE_EXPIRE.value)

        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir, exist_ok=True)

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)

        # 更新历史信息（PersistentWrapper 会在 step() 中追加）
        self.history = self.env.get_history()

        # 先递增步计数（现在 current_step 对应刚刚执行完的 env.step）
        self.current_step += 1

        # 保存当前步骤的快照
        self.save_step_svg()

        return obs, reward, terminated, truncated, info

    def reset(self, **kwargs):
        obs = self.env.reset(**kwargs)
        # 重置计数器（初始帧为 0）
        self.current_step = 0
        self.history = self.env.get_history()
        # 保存初始帧（step 0）
        self.save_step_svg()
        return obs

    def save_step_svg(self):
        # 使用 current_step 作为要保存的时间戳
        step_idx = self.current_step

        # 文件名
        filename = f"step_{step_idx:04d}.svg"
        path = os.path.join(self.save_dir, filename)

        # 障碍物切片（保持和原来一致）
        wr = self._working_radius
        if wr > 0:
            obstacles = self.env.get_obstacles(ignore_borders=False)[wr:-wr, wr:-wr]
        else:
            obstacles = self.env.get_obstacles(ignore_borders=False)

        # 解包历史（每个 agent 的 AgentState 列表）
        full_history = self.env.decompress_history(self.history)

        # 为每个 agent 选取当前时刻应显示的单个状态（最后一个 step <= step_idx）
        current_history = []
        for agent_history in full_history:
            last_state = None
            # 从后往前找第一个 step <= step_idx
            for s in reversed(agent_history):
                # AgentState 可能有属性 .step，确保可比较
                if getattr(s, "step", None) is not None and s.step <= step_idx:
                    last_state = s
                    break
            # 如果没有找到（极少数情况），回退到第一个已有状态
            if last_state is None:
                last_state = agent_history[0]
            # IMPORTANT: 每个 agent 的历史要是长度为 1（因为我们用 episode_length=1 表示静态帧）
            current_history.append([last_state])

        # 颜色配置
        svg_settings = SvgSettings()
        agents_colors = {index: svg_settings.colors[index % len(svg_settings.colors)]
                         for index in range(self.grid_config.num_agents)}

        # 创建 GridHolder：episode_length=1 表示仅渲染这一帧
        grid_holder = GridHolder(
            width=len(obstacles),
            height=len(obstacles[0]),
            obstacles=obstacles,
            episode_length=1,
            history=current_history,
            obs_radius=self.grid_config.obs_radius,
            on_target=self.grid_config.on_target,
            colors=agents_colors,
            config=AnimationConfig(static=True),
            svg_settings=svg_settings
        )

        # 渲染并写文件
        animation = AnimationDrawer().create_animation(grid_holder)
        with open(path, "w") as f:
            f.write(animation.render())
        self.dh.set(CacheInfo.SVG_IMAGE.value, animation.render())
        # print(f"已保存步骤 {step_idx} 的SVG图像到: {path}")
