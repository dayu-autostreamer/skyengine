from sky_dag import sky_dag_v0  # 替换为你的环境文件名

# 创建环境
env = sky_dag_v0.SkyDagEnvironment(grid_size=(3, 3), num_agents=2)

# 重置环境
observations, infos = env.reset()

# 运行一个 episode（直到结束）
done = {agent: False for agent in env.agents}
while not all(done.values()):
    # 随机策略：为每个 agent 随机选择一个动作
    actions = {
        agent: env.action_space(agent).sample()
        for agent in env.agents if not done[agent]
    }

    # 执行一步
    observations, rewards, terminations, truncations, infos = env.step(actions)

    # 渲染当前状态（控制台打印）
    env.render()

    # 更新 done 状态
    done = terminations
